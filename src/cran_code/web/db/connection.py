"""Database connection management."""

from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import event
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool

from cran_code.share import get_share_dir

Base = declarative_base()

# Default to ~/.cran/cran.db to keep within existing share dir
_DEFAULT_DB_PATH = Path(get_share_dir()) / "cran.db"

_db_url = os.environ.get("CRAN_DATABASE_URL") or f"sqlite+aiosqlite:///{_DEFAULT_DB_PATH}"

_engine_kwargs: dict = {"echo": False, "future": True, "pool_pre_ping": True}
if _db_url.startswith("sqlite"):
    # SQLite: a default-sized QueuePool (5+10) exhausts quickly under the
    # concurrent load of the key proxy, usage metering and prompt gate.
    # aiosqlite connections are cheap, so skip pooling entirely and enable
    # WAL so readers are not blocked behind writers.
    _engine_kwargs["poolclass"] = NullPool

engine = create_async_engine(_db_url, **_engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,
    autoflush=False,
)


@event.listens_for(engine.sync_engine, "connect")
def _enable_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    if _db_url.startswith("sqlite"):
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()


async def _ensure_column(conn, table: str, column: str, ddl_type: str) -> None:
    """Idempotent manual migration: add a column when missing (no alembic)."""
    rows = (await conn.exec_driver_sql(f"PRAGMA table_info({table})")).fetchall()
    if rows and all(row[1] != column for row in rows):
        await conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {column} {ddl_type}")


async def init_db() -> None:
    """Create all tables if they do not exist, then apply manual column migrations."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # 2026-08-23: team display timezone for usage statistics
        await _ensure_column(conn, "teams", "timezone", "VARCHAR(64)")
