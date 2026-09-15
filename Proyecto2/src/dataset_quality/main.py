"""Punto de entrada HTTP de la plataforma de calidad de datasets."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from dataset_quality import __version__
from dataset_quality.api.artifacts import router as artifacts_router
from dataset_quality.api.duplicates import router as duplicates_router
from dataset_quality.api.pipeline import router as pipeline_router
from dataset_quality.db import check_database
from dataset_quality.storage import check_object_storage

STATIC_DIR = Path(__file__).parent / "static"


def _run_check(name: str, check: Any) -> dict[str, str]:
    """Ejecuta una comprobacion y la traduce a un resultado serializable."""
    try:
        check()
    # Se captura ancho a proposito: /health debe reportar el fallo, no propagarlo.
    except Exception as error:
        return {"name": name, "status": "down", "detail": f"{type(error).__name__}: {error}"}
    return {"name": name, "status": "up"}


def create_app() -> FastAPI:
    app = FastAPI(
        title="Dataset Quality & Versioning",
        version=__version__,
        docs_url="/docs",
    )

    @app.get("/health", tags=["infra"])
    def health() -> JSONResponse:
        """Verifica que la app, MariaDB y MinIO esten realmente arriba."""
        checks = [
            _run_check("mariadb", check_database),
            _run_check("minio", check_object_storage),
        ]
        healthy = all(check["status"] == "up" for check in checks)
        return JSONResponse(
            status_code=200 if healthy else 503,
            content={
                "status": "ok" if healthy else "degraded",
                "version": __version__,
                "checks": checks,
            },
        )

    @app.get("/api/config", tags=["infra"])
    def config() -> dict[str, object]:
        """Configuracion efectiva SIN secretos (util para depurar el entorno)."""
        from dataset_quality.settings import get_settings

        return get_settings().public_summary()

    app.include_router(artifacts_router)
    app.include_router(duplicates_router)
    app.include_router(pipeline_router)

    # El build de Vite (si existe). En desarrollo puede no estar compilado
    # todavia: la API sigue respondiendo y /docs tambien.
    if (STATIC_DIR / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    index_html = STATIC_DIR / "index.html"

    # `response_model=None`: el retorno es una union de Response y FastAPI
    # intentaria construir un modelo Pydantic a partir de ella.
    @app.get("/{full_path:path}", include_in_schema=False, response_model=None)
    def spa(full_path: str) -> FileResponse | JSONResponse:
        """Cualquier ruta de navegacion devuelve el index de la SPA."""
        del full_path
        if index_html.is_file():
            return FileResponse(index_html)
        return JSONResponse(
            content={
                "mensaje": "La app web no esta compilada.",
                "como": "npm --prefix web ci && npm --prefix web run build",
                "api": "/docs",
            }
        )

    return app


app = create_app()
