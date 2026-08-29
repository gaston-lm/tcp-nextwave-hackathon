#!/usr/bin/env python3
"""Apply all shared PostgreSQL table definitions and seed local dashboard data."""

import os
from pathlib import Path

import psycopg2
from psycopg2.errors import DuplicateTable
from dotenv import load_dotenv


ROOT = Path(__file__).parents[1]
DEFINITIONS = Path(__file__).parent / "db_table_definitions"


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
            cursor.execute("""
                INSERT INTO incidents (
                    incident_key, title, severity, status, country, provider_name, overview,
                    estimated_impact, approval_rate_drop, affected_transaction_count, agent_action, agent_action_at,
                    started_at, last_seen_at
                ) VALUES (
                    'URG-3159', 'Mercado Pago declines transfers from AR', 'urgent', 'monitoring',
                    'Argentina', 'Mercado Pago',
                    'Authorization declines are 4.6× above the expected baseline for Argentine bank transfers.',
                    5120000, 18.7, 1284,
                    'Rerouted eligible Argentine transfers to the secondary provider and notified merchant operations.',
                    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP - INTERVAL '45 minutes', CURRENT_TIMESTAMP
                ) ON CONFLICT (incident_key) DO UPDATE
                SET approval_rate_drop = EXCLUDED.approval_rate_drop
                RETURNING incident_key
            """)
    print("Database schema and local dashboard seed are ready.")


if __name__ == "__main__":
    main()
