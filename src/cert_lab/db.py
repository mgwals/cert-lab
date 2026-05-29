from __future__ import annotations

import os
from collections.abc import Generator
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

DEFAULT_DATABASE_URL = "sqlite:///./data/cert_lab.sqlite3"


def database_url_from_env() -> str:
    return os.environ.get("CERT_LAB_DATABASE_URL", DEFAULT_DATABASE_URL)


def ensure_sqlite_parent(database_url: str) -> None:
    if not database_url.startswith("sqlite:///"):
        return
    raw_path = database_url.removeprefix("sqlite:///")
    if raw_path == ":memory:":
        return
    Path(raw_path).parent.mkdir(parents=True, exist_ok=True)


def build_engine(database_url: str | None = None):
    database_url = database_url or database_url_from_env()
    ensure_sqlite_parent(database_url)
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    kwargs = {"connect_args": connect_args}
    if database_url in {"sqlite://", "sqlite:///:memory:"}:
        kwargs["poolclass"] = StaticPool
    return create_engine(database_url, **kwargs)


def init_db(engine) -> None:
    SQLModel.metadata.create_all(engine)


engine = build_engine()


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
