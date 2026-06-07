"""Database connection management."""

from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from kimi_cli.share import get_share_dir

Base = declarative_base()

# Default to ~/.kimi/cran.db to keep within existing share dir
_DEFAULT_DB_PATH = Path(get_share_dir()) / "cran.db"

_db_url = os.environ.get("CRAN_DATABASE_URL")
if _db_url is None:
    _db_url = f"sqlite+aiosqlite:///{_DEFAULT_DB_PATH}"

engine = create_async_engine(
    _db_url,
    echo=False,
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,
    autoflush=False,
)


async def init_db() -> None:
    """Create all tables if they do not exist."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
