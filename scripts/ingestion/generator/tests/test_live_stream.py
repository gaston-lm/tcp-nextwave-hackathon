import time
from datetime import UTC, datetime, timedelta

import pytest

from scripts.ingestion.generator.live_stream import (
    LiveStreamController,
    transactions_for_second,
    validate_rows_per_minute,
)


def test_live_second_keeps_timestamps_within_its_persisted_second():
    second = datetime(2026, 8, 30, 12, 34, 45)

    transactions = transactions_for_second(
        second=second,
        rows=5,
        transaction_id_start=900,
        seed=42,
        provider_rates=None,
        decline_rules=[],
    )

    assert [transaction.transaction_id for transaction in transactions] == list(
        range(900, 905)
    )
    assert all(transaction.issued_timestamp == second for transaction in transactions)


@pytest.mark.parametrize("value", [0, -1, 10_001, "1.5", True])
def test_live_rows_per_minute_requires_a_positive_integer_in_range(value):
    with pytest.raises(ValueError):
        validate_rows_per_minute(value)


def test_controller_resumes_after_the_latest_persisted_second():
    latest = datetime(2026, 8, 30, 12, 34, 45, tzinfo=UTC)

    class Cursor:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def execute(self, _):
            pass

        def fetchone(self):
            return (latest.replace(microsecond=0) + timedelta(seconds=1),)

    class Connection:
        def cursor(self):
            return Cursor()

        def close(self):
            pass

    controller = LiveStreamController(connect_database=Connection)

    assert controller.next_start_at() == datetime(2026, 8, 30, 12, 34, 46)


def test_controller_generates_and_inserts_the_first_persisted_second():
    inserted_batches = []

    class Cursor:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def execute(self, _):
            pass

        def fetchone(self):
            return (99,)

    class Connection:
        def cursor(self):
            return Cursor()

        def close(self):
            pass

    controller = LiveStreamController(
        connect_database=Connection,
        insert_batch=lambda _, batch: inserted_batches.append(batch) or len(batch),
    )
    controller.start(2, datetime(2026, 8, 30, 12, 34), None, [])

    deadline = time.monotonic() + 1
    while not inserted_batches and time.monotonic() < deadline:
        time.sleep(0.01)
    controller.stop()
    while controller.status()["running"] and time.monotonic() < deadline:
        time.sleep(0.01)

    assert len(inserted_batches) == 1
    assert inserted_batches[0][0].transaction_id == 100
    assert len(inserted_batches[0]) >= 1
