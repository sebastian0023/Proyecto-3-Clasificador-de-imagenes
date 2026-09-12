"""Acceso a MariaDB via SQLAlchemy."""

from __future__ import annotations

from functools import lru_cache

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from dataset_quality.settings import Settings, get_settings


@lru_cache
def get_engine() -> Engine:
    """Engine unico del proceso, con `pool_pre_ping` para reconectar solo."""
    settings = get_settings()
    return create_engine(settings.database_url, pool_pre_ping=True, future=True)


def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)


def check_database(settings: Settings | None = None) -> None:
    """Lanza una excepcion si MariaDB no responde. Usado por `/health`."""
    del settings  # el engine ya resuelve la configuracion
    with get_engine().connect() as connection:
        connection.execute(text("SELECT 1"))
