"""Bucle del worker: toma trabajos de la cola y los ejecuta fuera del request.

    python -m p3.worker.runner

Cada tipo de trabajo (`kind`) tiene un handler `(config, report) -> None`.
`report(progress, message)` escribe progreso y log en la BD en su propia
transaccion, para que la pagina los vea mientras el trabajo corre. Si el
handler lanza una excepcion, el trabajo queda `failed` con el mensaje y el
worker sigue con el siguiente.
"""

from __future__ import annotations

import logging
import socket
import time
from collections.abc import Callable, Mapping
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from p3.worker import jobs

Report = Callable[[float, str], None]
Handler = Callable[[dict[str, Any], Report], None]

logger = logging.getLogger("p3.worker")


def run_dummy(config: dict[str, Any], report: Report) -> None:
    """Trabajo de prueba del stack: avanza por pasos sin entrenar nada."""
    steps = int(config.get("steps", 5))
    seconds = float(config.get("seconds", 1.0))
    for step in range(1, steps + 1):
        time.sleep(seconds)
        report(step / steps, f"paso {step}/{steps}")
    if config.get("fail"):
        raise RuntimeError("error simulado por config.fail")


HANDLERS: Mapping[str, Handler] = {"dummy": run_dummy}


def run_once(
    session_factory: sessionmaker[Session], worker_id: str, handlers: Mapping[str, Handler]
) -> bool:
    """Procesa un trabajo si hay alguno en cola. Devuelve si proceso uno."""
    with session_factory.begin() as session:
        job = jobs.claim_next(session, worker_id)
        if job is None:
            return False
        job_id, kind, config = job.id, job.kind, dict(job.config)

    def report(progress: float, message: str) -> None:
        with session_factory.begin() as session:
            jobs.report_progress(session, job_id, progress, message)

    handler = handlers.get(kind)
    try:
        if handler is None:
            raise LookupError(f"No hay handler para el tipo de trabajo '{kind}'")
        handler(config, report)
    except Exception as error:
        logger.exception("El trabajo %s fallo", job_id)
        with session_factory.begin() as session:
            jobs.mark_failed(session, job_id, f"{type(error).__name__}: {error}")
    else:
        with session_factory.begin() as session:
            jobs.mark_succeeded(session, job_id)
    return True


def main() -> None:
    from p3.worker.settings import get_session_factory, get_settings

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    settings = get_settings()
    session_factory = get_session_factory()
    worker_id = socket.gethostname()

    with session_factory.begin() as session:
        recovered = jobs.recover_orphans(session)
    logger.info("worker %s listo; %d trabajo(s) huerfano(s) marcados failed", worker_id, recovered)

    while True:
        if not run_once(session_factory, worker_id, HANDLERS):
            time.sleep(settings.poll_seconds)


if __name__ == "__main__":
    main()
