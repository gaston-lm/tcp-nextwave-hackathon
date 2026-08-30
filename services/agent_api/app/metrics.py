"""Read-only, parameterized transaction metrics used by the anomaly detection agent."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import asyncpg

from .observability import traced_tool

DIMENSION_COLUMNS = {
    "merchant": "merchant_name",
    "provider": "provider_name",
    "payment_method": "method_name",
    "country": "country",
    "issuing_bank": "issuing_bank",
}

DIMENSION_MASKS = {
    "merchant": 16,
    "provider": 8,
    "payment_method": 4,
    "country": 2,
    "issuing_bank": 1,
}


class MetricsService:
    def __init__(
        self,
        pool: asyncpg.Pool,
        as_of: datetime | None = None,
    ) -> None:
        self.pool = pool
        reference = as_of or datetime.now(UTC)
        # Transactions use TIMESTAMP without time zone. The caller is responsible
        # for submitting a timestamp in the database's business time zone.
        reference = reference.replace(tzinfo=None)
        self.window_end = reference.replace(
            minute=reference.minute - (reference.minute % 5), second=0, microsecond=0
        )
        self.window_start = self.window_end - timedelta(minutes=5)

    @staticmethod
    def _validate_dimensions(dimensions: list[str]) -> list[str]:
        if not dimensions or len(dimensions) > 5:
            raise ValueError("Choose between one and five diagnostic dimensions")
        if len(set(dimensions)) != len(dimensions):
            raise ValueError("Diagnostic dimensions must be unique")
        invalid = set(dimensions) - DIMENSION_COLUMNS.keys()
        if invalid:
            raise ValueError(f"Unsupported diagnostic dimensions: {sorted(invalid)}")
        return dimensions

    @staticmethod
    def _validate_filters(filters: dict[str, str]) -> dict[str, str]:
        invalid = set(filters) - DIMENSION_COLUMNS.keys()
        if invalid:
            raise ValueError(f"Unsupported filters: {sorted(invalid)}")
        return filters

    @traced_tool(
        "get_current_window_overview", "Gets current and baseline acceptance metrics."
    )
    async def overview(self) -> dict[str, Any]:
        sql = """
            WITH current_window AS (
                SELECT count(*)::int AS attempts,
                       count(*) FILTER (WHERE NOT is_declined)::int AS approvals,
                       count(*) FILTER (WHERE is_declined)::int AS declines,
                       COALESCE(sum(value) FILTER (WHERE is_declined), 0)::float AS declined_value
                FROM transactions
                WHERE issued_timestamp >= $1 AND issued_timestamp < $2
            ), baseline AS (
                SELECT COALESCE(sum(attempts), 0)::int AS attempts,
                       COALESCE(sum(approvals), 0)::int AS approvals,
                       COALESCE(sum(declines), 0)::int AS declines
                FROM baseline_metrics
                WHERE weekday = EXTRACT(ISODOW FROM $1::timestamp)::smallint
                  AND dimensions_mask = 0
            )
            SELECT 'current_window' AS period, attempts, approvals, declines,
                   COALESCE(approvals::float / NULLIF(attempts, 0), 0) AS approval_rate,
                   declined_value
            FROM current_window
            UNION ALL
            SELECT 'baseline' AS period, attempts, approvals, declines,
                   COALESCE(approvals::float / NULLIF(attempts, 0), 0) AS approval_rate,
                   0::float AS declined_value
            FROM baseline
        """
        async with self.pool.acquire() as connection:
            records = await connection.fetch(sql, self.window_start, self.window_end)
        return {record["period"]: dict(record) for record in records}

    @traced_tool(
        "get_current_segment_metrics",
        "Compares a diagnostic grain with its stored baseline.",
    )
    async def segment_metrics(
        self,
        dimensions: list[str],
        filters: dict[str, str] | None = None,
        limit: int = 25,
    ) -> list[dict[str, Any]]:
        dimensions = self._validate_dimensions(dimensions)
        filters = self._validate_filters(filters or {})
        if not set(filters).issubset(dimensions):
            raise ValueError(
                "Filters must also be included in the requested dimensions"
            )
        limit = min(max(limit, 1), 50)
        columns = [DIMENSION_COLUMNS[dimension] for dimension in dimensions]
        dimensions_mask = sum(DIMENSION_MASKS[dimension] for dimension in dimensions)
        selected = ", ".join(columns)
        grouped = ", ".join(columns)
        filter_parts: list[str] = []
        values: list[Any] = [
            self.window_start,
            self.window_end,
            dimensions_mask,
        ]
        for dimension, value in filters.items():
            values.append(value)
            filter_parts.append(f"{DIMENSION_COLUMNS[dimension]} = ${len(values)}")
        where_filters = (" AND " + " AND ".join(filter_parts)) if filter_parts else ""
        join_condition = " AND ".join(
            f"c.{column} IS NOT DISTINCT FROM b.{column}" for column in columns
        )
        values.append(limit)
        sql = f"""
            WITH current_metrics AS (
                SELECT {selected},
                       count(*)::int AS attempts,
                       count(*) FILTER (WHERE NOT is_declined)::int AS approvals,
                       count(*) FILTER (WHERE is_declined)::int AS declines,
                       COALESCE(avg((NOT is_declined)::int)::float, 0) AS approval_rate,
                       COALESCE(sum(value) FILTER (WHERE is_declined), 0)::float AS declined_value
                FROM transactions
                WHERE issued_timestamp >= $1 AND issued_timestamp < $2 {where_filters}
                GROUP BY {grouped}
            ), stored_baselines AS (
                SELECT {selected},
                       b.attempts,
                       b.approval_rate
                FROM baseline_metrics b
                WHERE b.weekday = EXTRACT(ISODOW FROM $1::timestamp)::smallint
                  AND b.dimensions_mask = $3
            )
            SELECT c.*, b.attempts AS baseline_attempts,
                   b.approval_rate AS baseline_approval_rate,
                   c.approval_rate - b.approval_rate AS approval_rate_delta,
                   GREATEST(0, c.declines - c.attempts * (1 - b.approval_rate))::float
                     AS excess_declines
            FROM current_metrics c
            LEFT JOIN stored_baselines b ON {join_condition}
            ORDER BY approval_rate_delta ASC NULLS LAST, excess_declines DESC
            LIMIT ${len(values)}
        """
        async with self.pool.acquire() as connection:
            records = await connection.fetch(sql, *values)
        return [dict(record) for record in records]

    @traced_tool(
        "get_decline_code_distribution",
        "Gets decline-code distribution for a failing segment.",
    )
    async def decline_code_distribution(
        self, filters: dict[str, str], limit: int = 20
    ) -> list[dict[str, Any]]:
        filters = self._validate_filters(filters)
        if not filters:
            raise ValueError("At least one segment filter is required")
        values: list[Any] = [self.window_start, self.window_end]
        parts: list[str] = []
        for dimension, value in filters.items():
            values.append(value)
            parts.append(f"{DIMENSION_COLUMNS[dimension]} = ${len(values)}")
        values.append(min(max(limit, 1), 50))
        sql = f"""
            SELECT decline_code, count(*)::int AS decline_count,
                   (count(*)::float / sum(count(*)) OVER ()) AS decline_share
            FROM transactions
            WHERE issued_timestamp >= $1 AND issued_timestamp < $2
              AND is_declined
              AND {" AND ".join(parts)}
            GROUP BY decline_code
            ORDER BY decline_count DESC
            LIMIT ${len(values)}
        """
        async with self.pool.acquire() as connection:
            records = await connection.fetch(sql, *values)
        return [dict(record) for record in records]
