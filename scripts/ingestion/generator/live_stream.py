"""Generate and persist an accelerated synthetic transaction stream."""

from __future__ import annotations

import random
import sys
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parents[2]
for import_path in (BASE_DIR, PROJECT_ROOT):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from dataset_generator import (  # noqa: E402
    generate_transactions,
    validate_decline_rules,
    validate_provider_rates,
)

from scripts.ingestion.load_history import (  # noqa: E402
    Transaction,
    database_config,
    insert_transactions,
)

MAX_ROWS_PER_MINUTE = 10_000
VOLUME_STANDARD_DEVIATION_RATIO = 0.15
HOURLY_VOLUME_STANDARD_DEVIATION_RATIO = 0.35


def validate_rows_per_minute(value: object) -> int:
    if isinstance(value, bool):
        raise ValueError("Las transacciones por minuto deben ser un número entero")
    try:
        rows = int(value)
    except (TypeError, ValueError):
        raise ValueError(
            "Las transacciones por minuto deben ser un número entero"
        ) from None
    if str(rows) != str(value).strip() and not isinstance(value, int):
        raise ValueError("Las transacciones por minuto deben ser un número entero")
    if not 1 <= rows <= MAX_ROWS_PER_MINUTE:
        raise ValueError(
            f"Las transacciones por minuto deben estar entre 1 y {MAX_ROWS_PER_MINUTE}"
        )
    return rows


def transactions_for_second(
    second: datetime,
    rows: int,
    transaction_id_start: int,
    seed: int,
    provider_rates: dict[str, float],
    decline_rules: list[dict],
) -> list[Transaction]:
    """Build a second's rows, with event timestamps inside that exact second."""
    generated = generate_transactions(
        n=rows,
        seed=seed,
        provider_rates=provider_rates,
        decline_rules=decline_rules,
        start_date=second,
        end_date=second,
    )
    return [
        Transaction(
            **{
                **row,
                "transaction_id": transaction_id_start + offset,
                "issued_timestamp": datetime.fromisoformat(row["issued_timestamp"]),
            }
        )
        for offset, row in enumerate(generated)
    ]


def sample_rows_per_second(rng: random.Random, average_rows_per_minute: int) -> int:
    """Sample one second of volume while preserving the configured minute average."""
    average_rows = average_rows_per_minute / 60
    standard_deviation = max(1, average_rows * VOLUME_STANDARD_DEVIATION_RATIO)
    return max(1, round(rng.gauss(average_rows, standard_deviation)))


def sample_hourly_average(rng: random.Random, average_rows: int) -> int:
    """Choose a volume profile for a simulated hour."""
    standard_deviation = max(1, average_rows * HOURLY_VOLUME_STANDARD_DEVIATION_RATIO)
    return max(1, round(rng.gauss(average_rows, standard_deviation)))


class LiveStreamController:
    """Owns a stream clock where one real second equals one persisted second."""

    def __init__(
        self,
        connect_database: Callable[[], object] | None = None,
        insert_batch: Callable[[object, list[Transaction]], int] = insert_transactions,
    ):
        self._connect_database = connect_database or self._default_connection
        self._insert_batch = insert_batch
        self._lock = threading.RLock()
        self._stop_event: threading.Event | None = None
        self._thread: threading.Thread | None = None
        self._provider_rates: dict[str, float] | None = None
        self._decline_rules: list[dict] | None = None
        self._state = self._empty_state()

    @staticmethod
    def _empty_state() -> dict:
        return {
            "running": False,
            "stopping": False,
            "rows_per_minute": None,
            "simulated_timestamp": None,
            "batches": 0,
            "generated_rows": 0,
            "last_batch_rows": 0,
            "hourly_average_rows": None,
            "inserted_rows": 0,
            "last_error": None,
            "scenario": "normal",
        }

    @staticmethod
    def _default_connection():
        try:
            import psycopg2
            from dotenv import load_dotenv
        except ModuleNotFoundError as error:
            raise RuntimeError(
                "Faltan dependencias de ingestión. Instalá scripts/ingestion/requirements.txt"
            ) from error
        load_dotenv(PROJECT_ROOT / "data" / ".env")
        return psycopg2.connect(**database_config())

    def start(
        self,
        rows_per_minute: int,
        start_at: datetime | None,
        provider_rates: dict[str, float] | None,
        decline_rules: list[dict] | None,
    ) -> dict:
        rows_per_minute = validate_rows_per_minute(rows_per_minute)
        rates = validate_provider_rates(provider_rates)
        rules = validate_decline_rules(decline_rules, rates)
        start_at = self.next_start_at() if start_at is None else start_at
        start_at = start_at.replace(second=0, microsecond=0)

        with self._lock:
            if self._state["running"]:
                raise RuntimeError("La ingestión en vivo ya está activa")
            stop_event = threading.Event()
            self._stop_event = stop_event
            self._state = {
                **self._empty_state(),
                "running": True,
                "rows_per_minute": rows_per_minute,
                "simulated_timestamp": start_at.isoformat(sep=" "),
            }
            self._provider_rates = rates
            self._decline_rules = rules
            self._thread = threading.Thread(
                target=self._run,
                args=(stop_event, rows_per_minute, start_at),
                daemon=True,
                name="generator-live-ingestion",
            )
            self._thread.start()
            return self.status()

    def next_start_at(self) -> datetime:
        """Return the first whole simulated second after persisted transactions."""
        connection = self._connect_database()
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT COALESCE(
                        date_trunc('second', MAX(issued_timestamp)) + INTERVAL '1 second',
                        date_trunc('second', CURRENT_TIMESTAMP AT TIME ZONE 'UTC')
                    )
                    FROM transactions
                """)
                return cursor.fetchone()[0].replace(tzinfo=None)
        finally:
            connection.close()

    def update_configuration(
        self,
        provider_rates: dict[str, float] | None,
        decline_rules: list[dict] | None,
        scenario: str = "normal",
    ) -> dict:
        """Apply a new generation configuration at the next simulated second."""
        rates = validate_provider_rates(provider_rates)
        rules = validate_decline_rules(decline_rules, rates)
        with self._lock:
            if not self._state["running"]:
                raise RuntimeError("La ingestión en vivo no está activa")
            self._provider_rates = rates
            self._decline_rules = rules
            self._state["scenario"] = scenario
            return self.status()

    def stop(self) -> dict:
        with self._lock:
            if self._state["running"] and self._stop_event is not None:
                self._stop_event.set()
                self._state["stopping"] = True
            return self.status()

    def status(self) -> dict:
        with self._lock:
            return self._state.copy()

    def _run(self, stop_event, rows_per_minute, clock):
        connection = None
        try:
            connection = self._connect_database()
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT COALESCE(MAX(transaction_id), 0) FROM transactions"
                )
                next_transaction_id = cursor.fetchone()[0] + 1

            batch_number = 0
            volume_rng = random.Random(clock.isoformat())
            sampled_hour = None
            hourly_average_rows = rows_per_minute
            while not stop_event.is_set():
                batch_started = time.monotonic()
                with self._lock:
                    rates = self._provider_rates.copy()
                    rules = self._decline_rules.copy()
                hour = clock.replace(minute=0, second=0, microsecond=0)
                if hour != sampled_hour:
                    sampled_hour = hour
                    hourly_average_rows = sample_hourly_average(
                        volume_rng, rows_per_minute
                    )
                batch_rows = sample_rows_per_second(volume_rng, hourly_average_rows)
                rows = transactions_for_second(
                    clock,
                    batch_rows,
                    next_transaction_id,
                    seed=42 + batch_number,
                    provider_rates=rates,
                    decline_rules=rules,
                )
                inserted = self._insert_batch(connection, rows)
                next_transaction_id += len(rows)
                batch_number += 1
                clock += timedelta(seconds=1)
                with self._lock:
                    self._state.update(
                        {
                            "simulated_timestamp": clock.isoformat(sep=" "),
                            "batches": batch_number,
                            "generated_rows": self._state["generated_rows"] + len(rows),
                            "last_batch_rows": len(rows),
                            "hourly_average_rows": hourly_average_rows,
                            "inserted_rows": self._state["inserted_rows"] + inserted,
                        }
                    )
                # Do not catch up by emitting multiple persisted seconds at once if
                # generation or the database is slower than a second.
                stop_event.wait(max(0, 1 - (time.monotonic() - batch_started)))
        except Exception as error:
            with self._lock:
                self._state["last_error"] = str(error)
        finally:
            if connection is not None:
                connection.close()
            with self._lock:
                self._state["running"] = False
                self._state["stopping"] = False
