from datetime import datetime, timezone
from pathlib import Path

import pytest

from scripts.ingestion.load_history import IngestionError, read_transactions
from scripts.ingestion.stream_ingest import replay_transactions


def write_csv(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "transactions.csv"
    path.write_text(content, encoding="utf-8")
    return path


HEADER = (
    "country,provider_name,provider_id,method_name,method_id,merchant_name,merchant_id,issuing_bank,receiving_bank,transaction_id,"
    "issued_timestamp,is_declined,decline_code,currency,value_transaction_currency,value\n"
)


def test_reads_valid_csv(tmp_path):
    path = write_csv(tmp_path, HEADER + "AR,Pay,1,card,1,Merchant,1,Issuer,Receiver,99,2026-01-02T03:04:05,true,51,ARS,100.5,10\n")

    transactions = read_transactions(path)

    assert len(transactions) == 1
    assert transactions[0].merchant_id == 1
    assert transactions[0].is_declined is True
    assert transactions[0].value == 10.0


def test_rejects_missing_required_column(tmp_path):
    path = write_csv(tmp_path, "country,provider_name\nAR,Pay\n")

    with pytest.raises(IngestionError, match="Missing required column 'provider_id'"):
        read_transactions(path)


def test_rejects_invalid_integer(tmp_path):
    path = write_csv(tmp_path, HEADER + "AR,Pay,1,card,1,Merchant,not-an-id,Issuer,Receiver,99,2026-01-02T03:04:05,false,0,ARS,100.5,10\n")

    with pytest.raises(IngestionError, match="row 2: invalid integer in merchant_id"):
        read_transactions(path)


def test_rejects_extra_value_in_row(tmp_path):
    path = write_csv(tmp_path, HEADER + "AR,Pay,1,card,1,Merchant,1,Issuer,Receiver,99,2026-01-02T03:04:05,false,0,ARS,100.5,10,extra\n")

    with pytest.raises(IngestionError, match="row 2: too many values"):
        read_transactions(path)


def test_replays_transactions_in_configured_batches(monkeypatch, tmp_path):
    path = write_csv(tmp_path, HEADER + "AR,Pay,1,card,1,Merchant,1,Issuer,Receiver,99,2026-01-02T03:04:05,false,0,ARS,100.5,10\n" + "AR,Pay,1,card,1,Merchant,1,Issuer,Receiver,100,2026-01-02T03:04:06,false,0,ARS,100.5,10\n")
    batches = []
    monkeypatch.setattr("scripts.ingestion.stream_ingest.time.sleep", lambda _: None)

    inserted = replay_transactions(read_transactions(path), 1000, 1, lambda batch: batches.append(batch) or len(batch))

    assert inserted == 2
    assert [len(batch) for batch in batches] == [1, 1]
    assert all(item.issued_timestamp.date() == datetime.now(timezone.utc).date() for batch in batches for item in batch)
