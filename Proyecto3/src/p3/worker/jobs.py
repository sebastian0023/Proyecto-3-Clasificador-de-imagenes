"""Cola de trabajos de entrenamiento persistida en la BD relacional.

El endpoint HTTP solo inserta una fila y devuelve su id; el worker la toma y
reporta estado, progreso, logs y error en esa misma fila. Como todo vive en la
BD, recargar la pagina o reiniciar el backend no pierde nada (criterio 6.1).

Funciones puras sobre una `Session` que recibe el llamador: aqui no se leen
variables de entorno ni se crean engines. La transaccion la controla quien
llama (`sessionmaker.begin()`).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import JSON, DateTime, Engine, Float, Index, String, Text, select
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

# TEXT de MySQL/MariaDB se queda en 64 KB; los logs de un entrenamiento largo
# pueden pasarlo. En SQLite `Text` no tiene limite.
LongText = Text().with_variant(mysql.MEDIUMTEXT(), "mysql", "mariadb")

ORPHAN_ERROR = "El worker se reinicio mientras el trabajo corria; vuelve a lanzarlo."


def utcnow() -> datetime:
    return datetime.now(UTC)


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class Base(DeclarativeBase):
    """Metadata propia de P3: no se mezcla con las tablas de Proyecto2."""


class TrainingJob(Base):
    __tablename__ = "p3_training_jobs"
    __table_args__ = (Index("ix_p3_training_jobs_status_created", "status", "created_at"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    kind: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16), default=JobStatus.QUEUED)
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    logs: Mapped[str] = mapped_column(LongText, default="")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    worker_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


def create_schema(engine: Engine) -> None:
    """Crea las tablas de P3 que falten. Idempotente."""
    Base.metadata.create_all(engine)


def log_lines(job: TrainingJob) -> list[str]:
    return [line for line in job.logs.splitlines() if line]


def _append_log(job: TrainingJob, message: str) -> None:
    job.logs = f"{job.logs}{utcnow().isoformat(timespec='seconds')} {message}\n"


def _require(session: Session, job_id: str) -> TrainingJob:
    job = session.get(TrainingJob, job_id)
    if job is None:
        raise LookupError(f"No existe el trabajo {job_id}")
    return job


def enqueue(session: Session, kind: str, config: dict[str, Any]) -> TrainingJob:
    job = TrainingJob(
        id=uuid.uuid4().hex,
        kind=kind,
        status=JobStatus.QUEUED,
        progress=0.0,
        config=config,
        logs="",
        created_at=utcnow(),
    )
    _append_log(job, f"encolado ({kind})")
    session.add(job)
    session.flush()
    return job


def get_job(session: Session, job_id: str) -> TrainingJob | None:
    return session.get(TrainingJob, job_id)


def claim_next(session: Session, worker_id: str) -> TrainingJob | None:
    """Toma el trabajo en cola mas antiguo y lo marca `running`.

    `SKIP LOCKED` hace que dos workers nunca tomen la misma fila en MariaDB;
    en SQLite (pruebas) la clausula se omite y la escritura ya es exclusiva.
    """
    statement = (
        select(TrainingJob)
        .where(TrainingJob.status == JobStatus.QUEUED)
        .order_by(TrainingJob.created_at, TrainingJob.id)
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    job = session.scalars(statement).first()
    if job is None:
        return None
    job.status = JobStatus.RUNNING
    job.worker_id = worker_id
    job.started_at = utcnow()
    _append_log(job, f"tomado por {worker_id}")
    session.flush()
    return job


def report_progress(
    session: Session, job_id: str, progress: float, message: str | None = None
) -> None:
    if not 0.0 <= progress <= 1.0:
        raise ValueError(f"progress debe estar entre 0 y 1, llego {progress}")
    job = _require(session, job_id)
    job.progress = progress
    if message:
        _append_log(job, message)


def mark_succeeded(session: Session, job_id: str) -> None:
    job = _require(session, job_id)
    job.status = JobStatus.SUCCEEDED
    job.progress = 1.0
    job.finished_at = utcnow()
    _append_log(job, "terminado")


def mark_failed(session: Session, job_id: str, error: str) -> None:
    job = _require(session, job_id)
    job.status = JobStatus.FAILED
    job.error = error
    job.finished_at = utcnow()
    _append_log(job, f"fallo: {error}")


def recover_orphans(session: Session) -> int:
    """Marca `failed` los trabajos que quedaron `running` tras un reinicio.

    Se llama al arrancar el worker: si habia uno corriendo, murio con el
    proceso anterior. Dejarlo en `running` lo haria parecer vivo para siempre.
    """
    orphans = session.scalars(
        select(TrainingJob).where(TrainingJob.status == JobStatus.RUNNING)
    ).all()
    for job in orphans:
        job.status = JobStatus.FAILED
        job.error = ORPHAN_ERROR
        job.finished_at = utcnow()
        _append_log(job, ORPHAN_ERROR)
    return len(orphans)
