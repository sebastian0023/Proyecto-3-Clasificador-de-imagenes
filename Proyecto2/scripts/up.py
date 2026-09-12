"""Punto unico de arranque del entorno local (Frente 1 de la rubrica).

    python scripts/up.py

Orquesta, sin ningun paso manual:

  1. Crea `.env` desde `.env.example` si no existe.
  2. Construye la imagen de la app y levanta MariaDB + MinIO + app.
  3. Crea los buckets de MinIO (job idempotente `minio-init`).
  4. Espera a que los tres servicios reporten `healthy`.
  5. Verifica `/health` y muestra las URLs de trabajo.

Solo usa la libreria estandar: se ejecuta con un Python 3.12 limpio, sin
instalar nada en el host. Esto importa para la compuerta M1 de la rubrica
(clonar y arrancar siguiendo el README, en una maquina ajena).
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = REPO_ROOT / ".env"
ENV_EXAMPLE_PATH = REPO_ROOT / ".env.example"


def log(message: str) -> None:
    print(f"\n\033[35m==>\033[0m {message}", flush=True)


def fail(message: str) -> None:
    print(f"\n\033[31mError:\033[0m {message}", file=sys.stderr, flush=True)
    raise SystemExit(1)


def ensure_env_file() -> None:
    """Si no existe `.env`, lo crea desde la plantilla del entorno local."""
    if ENV_PATH.exists():
        return
    if not ENV_EXAMPLE_PATH.exists():
        fail(f"No existe {ENV_PATH.name} ni {ENV_EXAMPLE_PATH.name}.")
    shutil.copyfile(ENV_EXAMPLE_PATH, ENV_PATH)
    print(f"No se encontro .env; se creo una copia desde {ENV_EXAMPLE_PATH.name}.")


def read_env() -> dict[str, str]:
    """Parser minimo de `.env` (solo para saber en que puertos publicar avisos)."""
    values: dict[str, str] = {}
    for raw_line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def require_docker() -> None:
    if shutil.which("docker") is None:
        fail("Docker no esta en el PATH. Instala Docker Desktop y vuelve a intentar.")
    probe = subprocess.run(
        ["docker", "compose", "version"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if probe.returncode != 0:
        fail("`docker compose` no responde. Revisa que Docker Desktop este corriendo.")


def compose(*args: str, check: bool = True) -> int:
    """Ejecuta `docker compose ...` mostrando la salida en vivo."""
    command = ["docker", "compose", *args]
    print(f"\033[90m$ {' '.join(command)}\033[0m", flush=True)
    result = subprocess.run(command, cwd=REPO_ROOT, check=False)
    if check and result.returncode != 0:
        fail(f"`{' '.join(command)}` termino con codigo {result.returncode}.")
    return result.returncode


def wait_for_health(url: str, timeout_seconds: int = 90) -> dict[str, object] | None:
    """Consulta `/health` hasta que responda 200 o se agote el tiempo."""
    deadline = time.monotonic() + timeout_seconds
    last_body: dict[str, object] | None = None
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                return json.loads(response.read())
        except urllib.error.HTTPError as error:
            try:
                last_body = json.loads(error.read())
            except (ValueError, OSError):
                last_body = None
        except (urllib.error.URLError, OSError, ValueError):
            last_body = None
        time.sleep(2)
    return last_body


def main() -> None:
    parser = argparse.ArgumentParser(description="Levanta el entorno local completo.")
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="Borra volumenes (BD y buckets) antes de levantar. Destructivo.",
    )
    parser.add_argument(
        "--no-build",
        action="store_true",
        help="No reconstruye la imagen de la app (arranque mas rapido).",
    )
    parser.add_argument(
        "--logs",
        action="store_true",
        help="Al terminar, sigue los logs de la app (Ctrl+C solo corta los logs).",
    )
    args = parser.parse_args()

    require_docker()
    ensure_env_file()
    env = read_env()
    app_port = env.get("APP_PORT", "8000")
    console_port = env.get("MINIO_CONSOLE_PORT", "9101")

    if args.fresh:
        log("Borrando contenedores y volumenes previos (--fresh)...")
        compose("down", "-v", check=False)

    log("Levantando MariaDB + MinIO + app y esperando healthchecks...")
    up_args = ["up", "-d", "--wait"]
    if not args.no_build:
        up_args.insert(1, "--build")
    compose(*up_args)

    log("Verificando /health (MariaDB + MinIO desde la app)...")
    health = wait_for_health(f"http://localhost:{app_port}/health")
    if health is None or health.get("status") != "ok":
        print(json.dumps(health, indent=2, ensure_ascii=False) if health else "(sin respuesta)")
        fail(
            "La app arranco pero /health no esta OK. "
            "Revisa `docker compose logs app` y los valores de .env."
        )
    print(json.dumps(health, indent=2, ensure_ascii=False))

    print(
        f"""
\033[32mEntorno listo.\033[0m

  App / UI          http://localhost:{app_port}
  OpenAPI           http://localhost:{app_port}/docs
  Health            http://localhost:{app_port}/health
  Consola MinIO     http://localhost:{console_port}   (usuario y clave en .env)

  Logs              docker compose logs -f app
  Apagar            python scripts/down.py
"""
    )

    if args.logs:
        log("Siguiendo logs de la app (Ctrl+C corta los logs, no los contenedores)...")
        try:
            compose("logs", "-f", "app", check=False)
        except KeyboardInterrupt:
            print("\nLogs cortados. Los contenedores siguen corriendo.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrumpido.")
        raise SystemExit(130) from None
