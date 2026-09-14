"""Interfaz de linea de comandos del pipeline.

Cada tier es un subcomando. Se usa `argparse` de la libreria estandar en vez de
una libreria de CLI para no anadir una dependencia por un punado de comandos;
si el arbol crece, cambiar a Typer es mecanico.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dataset_quality import __version__
from dataset_quality.models.errors import DatasetValidationError

GREEN, YELLOW, RED, DIM, RESET = "\033[32m", "\033[33m", "\033[31m", "\033[90m", "\033[0m"
MAGENTA = "\033[35m"

STATUS_COLOR = {"pass": GREEN, "fail": RED, "skipped": DIM}


def heading(text: str) -> None:
    print(f"\n{MAGENTA}==>{RESET} {text}")


def _progress(done: int, total: int) -> None:
    """Avance de la subida, en la misma linea."""
    if done % 25 and done != total:
        return
    width = 28
    filled = int(width * done / total)
    bar = "#" * filled + "." * (width - filled)
    end = "\n" if done == total else ""
    print(f"\r  [{bar}] {done}/{total}", end=end, flush=True)


def cmd_ingest(args: argparse.Namespace) -> int:
    """Tier 1 — valida el COCO, sube las imagenes a MinIO y puebla MariaDB."""
    from dataset_quality.tiers import ingest

    heading("Tier 1 — ingesta")
    try:
        summary = ingest.run(on_progress=None if args.quiet else _progress)
    except DatasetValidationError as error:
        print(f"\n{RED}El dataset no paso la validacion:{RESET}\n{error}", file=sys.stderr)
        return 1

    print(f"\n{GREEN}Ingesta completa.{RESET}")
    print(
        f"  MariaDB   {summary.images} imagenes, {summary.annotations} cajas, "
        f"{summary.categories} clases"
    )
    print(
        f"  MinIO     bucket `{summary.bucket}` — {summary.uploaded} subidas, "
        f"{summary.already_stored} ya estaban"
    )
    print(
        f"\n{DIM}Los binarios viven en MinIO; en MariaDB queda su llave "
        f"(`images.storage_key`).{RESET}"
    )
    return 0


def cmd_analyze(args: argparse.Namespace) -> int:
    """Tier 2 — corre los cinco analizadores y la descriptiva.

    Solo MIDE: aunque un check salga en `fail`, este comando termina en 0. La
    decision de bloquear un release es del Frente 4.
    """
    from dataset_quality.analyzers import describe, run_all
    from dataset_quality.models.coco import load_coco
    from dataset_quality.models.quality import QualityConfig
    from dataset_quality.tiers.ingest import RAW_ANNOTATIONS, RAW_IMAGES

    try:
        dataset = load_coco(RAW_ANNOTATIONS)
        config = QualityConfig.from_yaml(Path(args.config))
    except DatasetValidationError as error:
        print(f"\n{RED}{error}{RESET}", file=sys.stderr)
        return 1

    stats = describe(dataset)
    heading("Descriptiva")
    print(
        f"  {stats.totals.images} imagenes, {stats.totals.annotations} cajas, "
        f"{stats.totals.categories} clases"
    )
    print(
        f"  {stats.annotations_per_image:.2f} cajas por imagen, "
        f"{stats.images_without_annotations} imagenes sin anotar"
    )
    print(f"  area mediana de caja: {stats.median_box_area_ratio:.1%} de su imagen")
    for name, count in sorted(stats.images_per_class.items(), key=lambda item: -item[1]):
        print(f"    {name:<14}{count:>6} imagenes  ({stats.boxes_per_class[name]} cajas)")

    heading("Analizadores")
    results = run_all(dataset, config, RAW_IMAGES)
    for result in results:
        color = STATUS_COLOR[result.status]
        print(
            f"\n  {color}{result.status.upper():<7}{RESET} {result.name}  "
            f"{DIM}[{result.severity}]{RESET}"
        )
        print(f"          {result.message}")
        if result.offenders:
            muestra = ", ".join(str(item) for item in result.offenders[:5])
            print(f"          {DIM}infractores: {len(result.offenders)} (ej. {muestra}){RESET}")

    fallos = [result for result in results if result.status == "fail"]
    print(f"\n{len(fallos)} check(s) en fail. {DIM}El Tier 2 mide; bloquear es del Tier 3.{RESET}")

    if args.json:
        import json

        destino = Path(args.json)
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(
            json.dumps(
                {
                    "stats": stats.model_dump(),
                    "checks": [result.model_dump() for result in results],
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        print(f"Escrito {destino}")

    return 0


def _run_gate(args: argparse.Namespace):
    """Carga, analiza y evalua. Aislado para poder probar el CLI sin datos."""
    from dataset_quality.models.coco import load_coco
    from dataset_quality.models.quality import QualityConfig
    from dataset_quality.tiers import gate
    from dataset_quality.tiers.ingest import RAW_ANNOTATIONS, RAW_IMAGES

    dataset = load_coco(RAW_ANNOTATIONS)
    config = QualityConfig.from_yaml(Path(args.config))
    return gate.run(dataset, config, RAW_IMAGES, out=Path(args.out))


def cmd_gate(args: argparse.Namespace) -> int:
    """Tier 3 — evalua la politica y DEVUELVE el codigo de salida.

    Este `return report.exit_code` es la linea que hace que la compuerta sirva:
    sin ella el reporte diria `fail`, el terminal lo pintaria en rojo, y la
    etapa siguiente del pipeline se ejecutaria igual.
    """
    try:
        report = _run_gate(args)
    except DatasetValidationError as error:
        print(f"\n{RED}{error}{RESET}", file=sys.stderr)
        return 1

    heading("Compuerta de calidad")
    for check in report.checks:
        color = STATUS_COLOR[check.status]
        print(
            f"  {color}{check.status.upper():<7}{RESET} {check.name:<22} "
            f"{check.observed:>10.4g} contra {check.threshold:<10.4g} "
            f"{DIM}[{check.severity}]{RESET}"
        )
        print(f"          {DIM}{check.message}{RESET}")

    from dataset_quality.tiers import gate as gate_module

    bloquean = gate_module.blocking(report.checks)
    avisos = gate_module.warnings(report.checks)

    print(f"\nreporte: {args.out}")
    print(f"  huella:  {report.dataset_fingerprint[:16]}...")

    if report.exit_code == 0:
        print(f"\n{GREEN}La compuerta pasa.{RESET} {len(avisos)} aviso(s) que no bloquean.")
    else:
        nombres = ", ".join(check.name for check in bloquean)
        print(f"\n{RED}RELEASE BLOQUEADO{RESET} por {len(bloquean)} check(s): {nombres}")
        print(f"{DIM}La etapa siguiente del pipeline no se ejecuta.{RESET}")

    return report.exit_code


def cmd_init_db(args: argparse.Namespace) -> int:
    """Crea las tablas que falten. Idempotente."""
    del args
    from dataset_quality.db import create_schema

    create_schema()
    print("Esquema creado.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dq", description="Calidad y versionado de datasets COCO."
    )
    parser.add_argument("--version", action="version", version=__version__)
    subcommands = parser.add_subparsers(dest="command", required=True)

    ingest = subcommands.add_parser(
        "ingest", help="Tier 1 — valida el COCO, sube imagenes a MinIO y puebla MariaDB."
    )
    ingest.add_argument("--quiet", action="store_true", help="Sin barra de progreso.")
    ingest.set_defaults(handler=cmd_ingest)

    analyze = subcommands.add_parser(
        "analyze", help="Tier 2 — corre los cinco analizadores y la descriptiva."
    )
    analyze.add_argument("--config", default="quality.yaml", help="Ruta de quality.yaml.")
    analyze.add_argument("--json", default=None, help="Escribe el resultado en este JSON.")
    analyze.set_defaults(handler=cmd_analyze)

    gate = subcommands.add_parser(
        "gate", help="Tier 3 — evalua la politica; sale con codigo != 0 si bloquea."
    )
    gate.add_argument("--config", default="quality.yaml", help="Ruta de quality.yaml.")
    gate.add_argument("--out", default="reports/quality.json", help="Donde escribir el reporte.")
    gate.set_defaults(handler=cmd_gate)

    init_db = subcommands.add_parser("init-db", help="Crea las tablas que falten.")
    init_db.set_defaults(handler=cmd_init_db)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.handler(args))


def run() -> None:
    """Punto de entrada declarado en `pyproject.toml`."""
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nInterrumpido.")
        raise SystemExit(130) from None


if __name__ == "__main__":
    run()
