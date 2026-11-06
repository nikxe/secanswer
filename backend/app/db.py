"""Thin Postgres connection helper (psycopg 3)."""
import psycopg

from .config import settings


def get_conn() -> psycopg.Connection:
    """Return a new connection. Callers use it as a context manager."""
    return psycopg.connect(settings.database_url, autocommit=True)
