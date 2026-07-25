"""SQLite engine and session construction without global mutable state."""

import sqlite3

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker


def create_engine_for_url(database_url: str) -> Engine:
    """Create a SQLite engine with foreign-key enforcement enabled."""

    if not database_url.startswith("sqlite:///"):
        raise ValueError("Only sqlite:/// database URLs are supported during the MVP")
    engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def enable_sqlite_foreign_keys(
        connection: sqlite3.Connection,
        _connection_record: object,
    ) -> None:
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Create an explicit unit-of-work factory for repository injection."""

    return sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
