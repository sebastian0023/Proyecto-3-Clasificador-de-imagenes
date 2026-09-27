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
from pathlib import Path
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


def make_train_handler(
    *, data_dir: Path, device: str, pretrained: bool = True, num_workers: int = 0
) -> Handler:
    """Handler de `kind: "train"`: entrena sobre un manifiesto y reporta cada epoca.

    `data_dir` contiene `manifests/<manifest_id>/manifest.jsonl` y
    `crops/<release_id>/crops.jsonl` (salidas de F3 y de `generate_crops.py`).
    PyTorch se importa aqui para que la app de P2, que importa este paquete, no
    lo necesite.
    """

    def run_train(config: dict[str, Any], report: Report) -> None:
        from p3.data import dataset
        from p3.train import trainer
        from p3.train.config import TrainingConfig

        training = TrainingConfig.model_validate(config["training"])
        rows = dataset.load_manifest(
            data_dir / "manifests" / config["manifest_id"] / "manifest.jsonl"
        )
        releases = {row["release_id"] for row in rows}
        if len(releases) != 1:
            raise ValueError(f"El manifiesto mezcla releases: {sorted(releases)}")
        crop_index = dataset.load_crop_index(data_dir / "crops" / releases.pop())
        datasets = dataset.build_datasets(rows, crop_index, image_size=training.image_size)
        num_classes = len({row["class_index"] for row in rows})
        report(0.0, f"entorno: {trainer.environment_info(device)}")

        def on_epoch(metrics: dict[str, float]) -> None:
            epoch = int(metrics["epoch"])
            report(
                epoch / training.max_epochs,
                f"epoca {epoch}/{training.max_epochs} "
                f"train_loss={metrics['train_loss']:.4f} train_acc={metrics['train_accuracy']:.4f} "
                f"val_loss={metrics['val_loss']:.4f} val_acc={metrics['val_accuracy']:.4f}",
            )

        trainer.train(
            training,
            train_set=datasets["train"],
            val_set=datasets["val"],
            num_classes=num_classes,
            pretrained=pretrained,
            device=device,
            num_workers=num_workers,
            on_epoch=on_epoch,
        )

    return run_train


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
    handlers = {
        **HANDLERS,
        "train": make_train_handler(
            data_dir=settings.data_dir,
            device=settings.resolved_device(),
            num_workers=settings.num_workers,
        ),
    }

    with session_factory.begin() as session:
        recovered = jobs.recover_orphans(session)
    logger.info("worker %s listo; %d trabajo(s) huerfano(s) marcados failed", worker_id, recovered)

    while True:
        if not run_once(session_factory, worker_id, handlers):
            time.sleep(settings.poll_seconds)


if __name__ == "__main__":
    main()
