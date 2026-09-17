"""El MCP solo puede leer reportes validados y devolver evidencia citable."""

from __future__ import annotations

import asyncio
import shutil
from pathlib import Path

import pytest
from fastapi import HTTPException

from dataset_quality.api import artifacts
from dataset_quality.copilot import tools
from dataset_quality.mcp_server import create_server


@pytest.fixture
def reports(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    original = artifacts.REPORTS
    for name in ("quality.json", "stats.json", "splits.json", "versions.json"):
        shutil.copy(original / name, tmp_path / name)
    monkeypatch.setattr(artifacts, "REPORTS", tmp_path)
    monkeypatch.setattr(
        artifacts,
        "ARTIFACTS",
        {
            name: artifacts.Artifact(
                item.name, tmp_path / item.path.name, item.model, item.produced_by
            )
            for name, item in artifacts.ARTIFACTS.items()
        },
    )
    return tmp_path


def test_las_herramientas_son_cinco_y_solo_lectura(reports: Path) -> None:
    before = {path.name: path.read_bytes() for path in reports.iterdir()}

    results = [
        tools.get_quality_report(),
        tools.get_failed_checks(),
        tools.get_class_distribution(),
        tools.get_split_report(),
        tools.list_versions(),
    ]

    assert tools.ALLOWED_TOOL_NAMES == (
        "get_quality_report",
        "get_failed_checks",
        "get_class_distribution",
        "get_split_report",
        "list_versions",
    )
    assert all(len(result.source.artifact_revision) == 64 for result in results)
    assert {path.name: path.read_bytes() for path in reports.iterdir()} == before


def test_las_herramientas_devuelven_resumenes_citables(reports: Path) -> None:
    failed = tools.get_failed_checks(severity="error")
    distribution = tools.get_class_distribution()
    splits = tools.get_split_report()
    versions = tools.list_versions(limit=1)

    assert failed.source.artifact == "quality.json"
    assert all(check["severity"] == "error" for check in failed.data["checks"])
    assert distribution.source.artifact == "stats.json"
    assert distribution.data["images_per_class"]
    assert splits.data["counts"].keys() == {"train", "val", "test"}
    assert len(versions.data["versions"]) == 1


def test_un_reporte_invalido_no_produce_evidencia(reports: Path) -> None:
    (reports / "stats.json").write_text('{"stats": "roto"}', encoding="utf-8")

    with pytest.raises(HTTPException, match=r"stats\.json"):
        tools.get_class_distribution()


def test_el_despachador_rechaza_herramientas_y_argumentos_no_permitidos(reports: Path) -> None:
    with pytest.raises(ValueError, match="no permitida"):
        tools.execute_tool("delete_dataset")
    with pytest.raises(ValueError, match="no acepta argumentos"):
        tools.execute_tool("get_split_report", {"path": "reports/quality.json"})


def test_el_servidor_mcp_descubre_y_ejecuta_las_cinco_herramientas() -> None:
    from mcp import Client

    async def discover() -> tuple[list[str], object]:
        async with Client(create_server()) as client:
            listed = await client.list_tools()
            result = await client.call_tool("get_quality_report", {})
            return [tool.name for tool in listed.tools], result

    names, result = asyncio.run(discover())

    assert names == list(tools.ALLOWED_TOOL_NAMES)
    assert result.is_error is False
    assert result.content[0].text.startswith("{")
