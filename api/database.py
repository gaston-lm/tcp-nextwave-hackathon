"""PostgreSQL connection helpers for the dashboard API."""

import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv


def connect():
    load_dotenv(Path(__file__).parents[1] / "data" / ".env")
    return psycopg2.connect(
        host=os.environ["POSTGRES_HOST"],
        port=os.environ["POSTGRES_PORT"],
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    )
