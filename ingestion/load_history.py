#!/usr/bin/env python3
"""Load a historical payment transaction CSV into PostgreSQL."""

from __future__ import annotations

import argparse
import csv
import logging
import math
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

CSV_COLUMNS = (
    "country", "provider_name", "provider_id", "method_name", "method_id",
    "merchant_name", "merchant_id", "issuing_bank", "receiving_bank",
    "transaction_id", "issued_timestamp", "is_declined", "decline_code",
    "currency", "value_transaction_currency", "value",
)


class IngestionError(ValueError):
    """An input or lookup error that can be shown directly to the runner."""


@dataclass(frozen=True)
class Transaction:
    country: str
    provider_name: str
    provider_id: int
    method_name: str
    method_id: int
    merchant_name: str
    merchant_id: int
    issuing_bank: str
    receiving_bank: str
    transaction_id: int
    issued_timestamp: datetime
    is_declined: bool
    decline_code: int
    currency: str
    value_transaction_currency: float
    value: float


def _required(value: str | None, column: str, row_number: int) -> str:
    if value is None or not value.strip():
        raise IngestionError(f"Error processing row {row_number}: {column} is required")
    return value.strip()


def _integer(value: str | None, column: str, row_number: int) -> int:
    text = _required(value, column, row_number)
    try:
        if text.startswith(("+", "-")):
            digits = text[1:]
        else:
            digits = text
        if not digits.isdigit():
            raise ValueError
        return int(text)
    except ValueError as error:
        raise IngestionError(
            f"Error processing row {row_number}: invalid integer in {column}: {text!r}"
        ) from error


def _number(value: str | None, column: str, row_number: int) -> float:
    text = _required(value, column, row_number)
    try:
        parsed = float(text)
    except ValueError as error:
        raise IngestionError(
            f"Error processing row {row_number}: invalid number in {column}: {text!r}"
        ) from error
    if not math.isfinite(parsed):
        raise IngestionError(
            f"Error processing row {row_number}: invalid number in {column}: {text!r}"
        )
    return parsed


def _boolean(value: str | None, column: str, row_number: int) -> bool:
    text = _required(value, column, row_number).lower()
    values = {"true": True, "false": False, "1": True, "0": False}
    if text not in values:
        raise IngestionError(
            f"Error processing row {row_number}: invalid boolean in {column}: {text!r}"
        )
    return values[text]


def _timestamp(value: str | None, column: str, row_number: int) -> datetime:
    text = _required(value, column, row_number)
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as error:
        raise IngestionError(
            f"Error processing row {row_number}: invalid timestamp in {column}: {text!r}"
        ) from error


def iter_transactions(path: Path) -> Iterable[Transaction]:
    """Yield validated CSV rows without holding the full file in memory."""
    try:
        with path.open(newline="", encoding="utf-8-sig") as csv_file:
            reader = csv.DictReader(csv_file)
            received_columns = tuple(reader.fieldnames or ())
            missing = [column for column in CSV_COLUMNS if column not in received_columns]
            unexpected = [column for column in received_columns if column not in CSV_COLUMNS]
            if missing:
                raise IngestionError(f"Missing required column {missing[0]!r}")
            if unexpected:
                raise IngestionError(f"Unexpected column {unexpected[0]!r}")

            for row_number, row in enumerate(reader, start=2):
                if None in row:
                    raise IngestionError(
                        f"Error processing row {row_number}: too many values for the CSV header"
                    )
                yield Transaction(
                    country=_required(row["country"], "country", row_number),
                    provider_name=_required(row["provider_name"], "provider_name", row_number),
                    provider_id=_integer(row["provider_id"], "provider_id", row_number),
                    method_name=_required(row["method_name"], "method_name", row_number),
                    method_id=_integer(row["method_id"], "method_id", row_number),
                    merchant_name=_required(row["merchant_name"], "merchant_name", row_number),
                    merchant_id=_integer(row["merchant_id"], "merchant_id", row_number),
                    issuing_bank=_required(row["issuing_bank"], "issuing_bank", row_number),
                    receiving_bank=_required(row["receiving_bank"], "receiving_bank", row_number),
                    transaction_id=_integer(row["transaction_id"], "transaction_id", row_number),
                    issued_timestamp=_timestamp(row["issued_timestamp"], "issued_timestamp", row_number),
                    is_declined=_boolean(row["is_declined"], "is_declined", row_number),
                    decline_code=_integer(row["decline_code"], "decline_code", row_number),
                    currency=_required(row["currency"], "currency", row_number),
                    value_transaction_currency=_number(row["value_transaction_currency"], "value_transaction_currency", row_number),
                    value=_number(row["value"], "value", row_number),
                )
    except FileNotFoundError as error:
        raise IngestionError(f"CSV file not found: {path}") from error
    except csv.Error as error:
        raise IngestionError(f"Unable to parse CSV: {error}") from error


def read_transactions(path: Path) -> list[Transaction]:
    """Read and validate all rows, failing at the first invalid one."""
    return list(iter_transactions(path))


def database_config() -> dict[str, str]:
    required = ("POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD")
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise IngestionError(f"Missing required environment variable {missing[0]}")
    return {
        "host": os.environ["POSTGRES_HOST"], "port": os.environ["POSTGRES_PORT"],
        "dbname": os.environ["POSTGRES_DB"], "user": os.environ["POSTGRES_USER"],
        "password": os.environ["POSTGRES_PASSWORD"],
    }


def insert_transactions(connection, transactions: Iterable[Transaction]) -> int:
    """Resolve schema-required IDs and bulk insert rows in one transaction."""
    transaction_rows = list(transactions)
    if not transaction_rows:
        return 0

    values = [(
        item.country, item.provider_name, item.provider_id, item.method_name,
        item.method_id, item.merchant_name, item.merchant_id, item.issuing_bank,
        item.receiving_bank, item.transaction_id, item.issued_timestamp,
        item.is_declined, item.decline_code, item.currency,
        item.value_transaction_currency, item.value,
    ) for item in transaction_rows]
    providers = {
        (item.merchant_id, item.provider_id):
            (item.merchant_id, item.merchant_name, item.provider_id, item.provider_name)
        for item in transaction_rows
    }
    methods = {
        (item.provider_id, item.method_id):
            (item.provider_id, item.provider_name, item.method_id, item.method_name)
        for item in transaction_rows
    }
    with connection.cursor() as cursor:
        from psycopg2.extras import execute_values
        execute_values(cursor, """
            INSERT INTO providers_by_merchant (merchant_id, merchant_name, provider_id, provider_name)
            VALUES %s
            ON CONFLICT (merchant_id, provider_id) DO UPDATE
            SET merchant_name = EXCLUDED.merchant_name, provider_name = EXCLUDED.provider_name
        """, list(providers.values()), page_size=1000)
        execute_values(cursor, """
            INSERT INTO methods_by_provider (provider_id, provider_name, method_id, method_name)
            VALUES %s
            ON CONFLICT (provider_id, method_id) DO UPDATE
            SET provider_name = EXCLUDED.provider_name, method_name = EXCLUDED.method_name
        """, list(methods.values()), page_size=1000)
        inserted_rows = execute_values(cursor, """
            INSERT INTO transactions (
                country, provider_name, provider_id, method_name, method_id, merchant_name, merchant_id,
                issuing_bank, receiving_bank, transaction_id, issued_timestamp, is_declined,
                decline_code, currency, value_transaction_currency, value
            ) VALUES %s
            ON CONFLICT (transaction_id) DO NOTHING
            RETURNING transaction_id
        """, values, page_size=1000, fetch=True)
    connection.commit()
    return len(inserted_rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Load a historical payment transaction CSV into PostgreSQL.")
    parser.add_argument("csv_file", type=Path, help="Path to the history CSV file")
    args = parser.parse_args(argv)
    started = time.monotonic()
    try:
        try:
            from dotenv import load_dotenv
            import psycopg2
        except ModuleNotFoundError as error:
            raise IngestionError(
                "Missing dependency. Install requirements with: pip install -r requirements.txt"
            ) from error
        load_dotenv(dotenv_path=Path(__file__).parents[1] / "data" / ".env")
        logging.basicConfig(level=logging.INFO, format="%(message)s")
        logging.info("Reading history from %s...", args.csv_file)
        transactions = read_transactions(args.csv_file)
        logging.info("Loaded %d rows. Validation successful.", len(transactions))

        logging.info("Inserting into PostgreSQL...")
        with psycopg2.connect(**database_config()) as connection:
            inserted = insert_transactions(connection, transactions)
        logging.info("Inserted %d rows successfully.", inserted)
        logging.info("Completed in %.1f seconds.", time.monotonic() - started)
        return 0
    except (IngestionError, OSError) as error:
        logging.error("Error: %s", error)
        return 1


if __name__ == "__main__":
    sys.exit(main())
