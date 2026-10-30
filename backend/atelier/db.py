"""SQLite engine + session plumbing."""

import logging
from collections.abc import Iterator

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from .config import get_settings
from .models import Base

settings = get_settings()

engine = create_engine(
    f"sqlite:///{settings.db_path}",
    connect_args={"check_same_thread": False},
)


@event.listens_for(engine, "connect")
def _enable_fk(dbapi_conn, _record):
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA foreign_keys=ON")
    cur.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


log = logging.getLogger(__name__)

# Columns added after the first release. SQLite can ADD COLUMN in place, which
# is enough for a local single-user app - no migration tool needed, and nobody
# loses their catalogued boards to a schema change.
_ADDED_COLUMNS: dict[str, dict[str, str]] = {
    "sources": {
        "ships": "VARCHAR(16) DEFAULT 'local'",
        "region": "VARCHAR(8)",
    },
}


def _apply_additive_migrations() -> None:
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    with engine.begin() as conn:
        for table, columns in _ADDED_COLUMNS.items():
            if table not in existing_tables:
                continue
            present = {c["name"] for c in inspector.get_columns(table)}
            for name, ddl in columns.items():
                if name not in present:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))
                    log.info("migrated: added %s.%s", table, name)


def init_db() -> None:
    _apply_additive_migrations()
    Base.metadata.create_all(engine)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
