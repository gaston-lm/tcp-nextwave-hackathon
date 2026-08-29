#!/usr/bin/env python3
"""Show the current transaction-ingestion status in PostgreSQL."""

from __future__ import annotations

import sys
from pathlib import Path

try:
    from .load_history import IngestionError, database_config
except ImportError:  # Allows `python ingestion/check_db.py`.
    from load_history import IngestionError, database_config


def main() -> int:
    try:
        try:
            from dotenv import load_dotenv
            import psycopg2
        except ModuleNotFoundError as error:
            raise IngestionError(
                "Missing dependency. Install requirements with: pip install -r requirements.txt"
            ) from error

        load_dotenv(dotenv_path=Path(__file__).parents[1] / "data" / ".env")
        with psycopg2.connect(**database_config()) as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT count(*), min(issued_timestamp), max(issued_timestamp)
                    FROM transactions
                """)
                count, oldest, newest = cursor.fetchone()
        print("Database connection: successful")
        print(f"Transactions: {count}")
        print(f"Oldest transaction timestamp: {oldest or 'none'}")
        print(f"Newest transaction timestamp: {newest or 'none'}")
        return 0
    except Exception as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
