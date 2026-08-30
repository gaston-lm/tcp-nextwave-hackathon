"""SQLAlchemy read models used by IncidentReviewer."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker

from .db_models import DeploymentLog, Incident, IncidentMemory
from .models import ActionableIncident, RecentIncident
from .observability import traced_tool

_DIMENSION_KEYS = (
    "merchant",
    "provider",
    "payment_method",
    "country",
    "issuing_bank",
)


def normalized_dimension_signatures(value: dict[str, Any]) -> dict[str, Any]:
    """Adapt legacy sparse JSONB signatures to the strict agent contract."""
    return {key: value.get(key) for key in _DIMENSION_KEYS}


class IncidentRepository:
    def __init__(self, session_factory: async_sessionmaker) -> None:
        self.session_factory = session_factory

    async def recent_open_incidents(self) -> list[RecentIncident]:
        statement = (
            select(Incident)
            .where(Incident.status == "open")
            .order_by(Incident.last_seen_at.desc())
        )
        async with self.session_factory() as session:
            incidents = list(await session.scalars(statement))
        return [
            RecentIncident(
                incident_id=item.incident_id,
                severity=item.severity,
                status=item.status,
                title=item.title,
                overview=item.overview,
                dimension_signatures=normalized_dimension_signatures(
                    item.dimension_signatures
                ),
                estimated_impact=item.estimated_impact,
                approval_rate_drop=item.approval_rate_drop,
                affected_transaction_count=item.affected_transaction_count,
                started_at=item.started_at,
                last_seen_at=item.last_seen_at,
            )
            for item in incidents
        ]

    async def new_incidents(self, incident_ids: list[int]) -> list[ActionableIncident]:
        if not incident_ids:
            return []
        statement = select(Incident).where(Incident.incident_id.in_(incident_ids))
        async with self.session_factory() as session:
            rows = list(await session.scalars(statement))
        by_id = {item.incident_id: item for item in rows}
        missing = set(incident_ids) - by_id.keys()
        if missing:
            raise ValueError(f"Cannot action missing incidents: {sorted(missing)}")
        return [
            ActionableIncident(
                incident_id=by_id[incident_id].incident_id,
                title=by_id[incident_id].title,
                overview=by_id[incident_id].overview,
                dimension_signatures=normalized_dimension_signatures(
                    by_id[incident_id].dimension_signatures
                ),
                related_deployment_ids=by_id[incident_id].related_deployments,
            )
            for incident_id in incident_ids
        ]

    @traced_tool(
        "get_merchant_provider_alternatives",
        "Lists providers accepted by a merchant excluding the affected provider.",
    )
    async def provider_alternatives(
        self, merchant: str, affected_provider: str
    ) -> list[dict[str, str]]:
        statement = text(
            """
            SELECT provider_name
            FROM providers_by_merchant
            WHERE merchant_name = :merchant
              AND provider_name <> :affected_provider
            ORDER BY provider_name
            """
        )
        async with self.session_factory() as session:
            rows = (
                (
                    await session.execute(
                        statement,
                        {"merchant": merchant, "affected_provider": affected_provider},
                    )
                )
                .mappings()
                .all()
            )
        return [{"provider": row["provider_name"]} for row in rows]

    @traced_tool(
        "search_closed_incidents",
        "Semantically searches closed incidents older than 24 hours.",
    )
    async def search_closed_incidents(
        self, embedding: list[float], limit: int = 5
    ) -> list[dict[str, Any]]:
        cutoff = datetime.now(UTC) - timedelta(hours=24)
        similarity = (1 - IncidentMemory.embedding.cosine_distance(embedding)).label(
            "similarity"
        )
        statement = (
            select(Incident, similarity)
            .join(IncidentMemory)
            .where(Incident.status == "closed", Incident.last_seen_at < cutoff)
            .order_by(IncidentMemory.embedding.cosine_distance(embedding))
            .limit(limit)
        )
        async with self.session_factory() as session:
            rows = (await session.execute(statement)).all()
        return [
            {
                "incident_id": item.incident_id,
                "title": item.title,
                "overview": item.overview,
                "dimension_signatures": item.dimension_signatures,
                "status": item.status,
                "last_seen_at": item.last_seen_at,
                "similarity": similarity_score,
            }
            for item, similarity_score in rows
        ]

    @traced_tool(
        "search_recent_deploys",
        "Semantically searches payment processor deployment logs.",
    )
    async def search_deployments(
        self, embedding: list[float], limit: int = 5
    ) -> list[dict[str, Any]]:
        similarity = (1 - DeploymentLog.embedding.cosine_distance(embedding)).label(
            "similarity"
        )
        statement = (
            select(DeploymentLog, similarity)
            .order_by(DeploymentLog.embedding.cosine_distance(embedding))
            .limit(limit)
        )
        async with self.session_factory() as session:
            rows = (await session.execute(statement)).all()
        return [
            {
                "deploy_id": item.deploy_id,
                "description_of_deploy": item.description_of_deploy,
                "dimensions_affected": item.dimensions_affected,
                "deployed_at": item.deployed_at,
                "similarity": similarity_score,
            }
            for item, similarity_score in rows
        ]
