#!/usr/bin/env python3
"""Apply all shared PostgreSQL table definitions and seed local dashboard data."""

import os
from pathlib import Path

import psycopg2
from psycopg2.errors import DuplicateTable
from dotenv import load_dotenv


ROOT = Path(__file__).parents[1]
DEFINITIONS = Path(__file__).parent / "db_table_definitions"
TEST_DASHBOARD_SEED = Path(__file__).parent / "test_mock_dashboard.sql"


def main() -> None:
    load_dotenv(Path(__file__).with_name(".env"))
    connection_config = {
        "host": os.environ["POSTGRES_HOST"],
        "port": os.environ["POSTGRES_PORT"],
        "dbname": os.environ["POSTGRES_DB"],
        "user": os.environ["POSTGRES_USER"],
        "password": os.environ["POSTGRES_PASSWORD"],
    }
    table_files = (
        "methods_by_provider.sql",
        "providers_by_merchant.sql",
        "transactions.sql",
        "incidents.sql",
    )
    with psycopg2.connect(**connection_config) as connection:
        with connection.cursor() as cursor:
            for filename in table_files:
                cursor.execute("SAVEPOINT apply_definition")
                try:
                    cursor.execute((DEFINITIONS / filename).read_text(encoding="utf-8"))
                except DuplicateTable:
                    cursor.execute("ROLLBACK TO SAVEPOINT apply_definition")
            cursor.execute(TEST_DASHBOARD_SEED.read_text(encoding="utf-8"))
    print("Database schema and local dashboard seed are ready.")


if __name__ == "__main__":
    main()
