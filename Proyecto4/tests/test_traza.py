"""F6, bloque 1: comparacion de una captura entre dispositivo, S3 y portal (sin AWS)."""

from __future__ import annotations

import argparse
import hashlib
import json

import pytest

import trazar_captura as tc

CID = "44e6a9b3-e5dc-4d92-a8e6-9c7e0a0c65b0"
FOTO = b"\xff\xd8\xff bytes de la foto"
SHA_FOTO = hashlib.sha256(FOTO).hexdigest()


def evento(**cambios: object) -> dict[str, object]:
    base: dict[str, object] = {
        "schema_version": 1,
        "capture_id": CID,
        "captured_at": "2026-10-12T21:10:21.399466+00:00",
        "device_id": "edge01",
        "model_version": "1.0.0-int8.1",
        "model_sha256": "ca689c4e1478ccca7821dffaba8f07886bd9609a8aa3cec7450d9f875fbd69c0",
        "image_sha256": SHA_FOTO,
        "image_ref": "edge01-44e6a9b3.jpg",
        "predicted_class": "person",
        "confidence": 0.9393,
    }
    base.update(cambios)
    return base


def registro(**cambios: object) -> dict[str, object]:
    """Lo que guarda el receptor: el evento mas los campos del servidor."""
    datos = evento(**cambios)
    datos.update(received_at="2026-10-12T21:10:22.281+00:00", warnings=[], region=None)
    return datos


def estados(filas: list[tc.Fila]) -> dict[str, str]:
    return {fila.campo: fila.estado for fila in filas}


# --- comparar_campos -----------------------------------------------------------


def test_tres_fuentes_iguales_coinciden():
    filas = tc.comparar_campos({"dispositivo": evento(), "S3": registro(), "portal": registro()})
    assert set(estados(filas).values()) == {tc.COINCIDE}
    assert [fila.campo for fila in filas] == list(tc.CAMPOS)


def test_campos_del_servidor_no_cuentan():
    # received_at y warnings existen solo en S3/portal: no son diferencias.
    filas = tc.comparar_campos({"dispositivo": evento(), "S3": registro()})
    assert tc.NO_COINCIDE not in estados(filas).values()


@pytest.mark.parametrize(
    ("campo", "valor"),
    [
        ("predicted_class", "dog"),
        ("confidence", 0.94),
        ("model_version", "1.0.0"),
        ("model_sha256", "0" * 64),
        ("captured_at", "2026-10-12T21:10:21+00:00"),
        ("image_sha256", "f" * 64),
    ],
)
def test_un_campo_distinto_no_coincide(campo, valor):
    filas = tc.comparar_campos(
        {"dispositivo": evento(), "S3": registro(**{campo: valor}), "portal": registro()}
    )
    resultado = estados(filas)
    assert resultado[campo] == tc.NO_COINCIDE
    assert [c for c, e in resultado.items() if e == tc.NO_COINCIDE] == [campo]


def test_confianza_identica_coincide_y_redondeada_no():
    same = tc.comparar_campos({"dispositivo": evento(confidence=0.9393), "S3": registro()})
    assert estados(same)["confidence"] == tc.COINCIDE
    otra = tc.comparar_campos(
        {"dispositivo": evento(confidence=0.939312), "S3": registro(confidence=0.9393)}
    )
    assert estados(otra)["confidence"] == tc.NO_COINCIDE


def test_campo_ausente_en_una_fuente_presente_no_coincide():
    sin_version = evento()
    del sin_version["model_version"]
    filas = tc.comparar_campos({"dispositivo": sin_version, "S3": registro()})
    fila = next(f for f in filas if f.campo == "model_version")
    assert fila.estado == tc.NO_COINCIDE
    assert fila.valores["dispositivo"] == tc.FALTA


def test_fuente_ausente_no_es_diferencia():
    filas = tc.comparar_campos({"dispositivo": None, "S3": registro(), "portal": registro()})
    assert set(estados(filas).values()) == {tc.COINCIDE}
    assert "dispositivo" not in filas[0].valores


def test_una_sola_fuente_queda_sin_comparar():
    filas = tc.comparar_campos({"dispositivo": None, "S3": registro(), "portal": None})
    assert set(estados(filas).values()) == {tc.SIN_COMPARAR}


def test_resumen_dice_que_nada_se_comparo_con_una_sola_fuente():
    traza = tc.Traza(CID, filas=tc.comparar_campos({"S3": registro()}))
    assert traza.codigo == 0
    assert "0 de 7 filas comparadas" in tc.formatear(traza)


# --- comparar_imagen -------------------------------------------------------------


def test_imagen_igual_en_todas_partes():
    fila = tc.comparar_imagen(
        {
            "dispositivo (foto local)": SHA_FOTO,
            "dispositivo (evento)": SHA_FOTO,
            "S3 (metadatos)": SHA_FOTO,
            "S3 (descarga)": SHA_FOTO,
            "portal (descarga)": SHA_FOTO,
        }
    )
    assert fila.estado == tc.COINCIDE
    assert len(fila.valores) == 5


def test_imagen_distinta_en_el_portal():
    fila = tc.comparar_imagen(
        {"S3 (metadatos)": SHA_FOTO, "S3 (descarga)": SHA_FOTO, "portal (descarga)": "a" * 64}
    )
    assert fila.estado == tc.NO_COINCIDE


def test_imagen_omite_fuentes_sin_dato():
    fila = tc.comparar_imagen({"dispositivo (foto local)": None, "S3 (descarga)": SHA_FOTO})
    assert fila.estado == tc.SIN_COMPARAR
    assert list(fila.valores) == ["S3 (descarga)"]


# --- buscar_evento ---------------------------------------------------------------


def test_busca_el_evento_por_id_y_cuenta_repeticiones():
    lineas = [
        json.dumps(evento(capture_id="otro")),
        "",
        json.dumps(evento(confidence=0.5)),
        json.dumps(evento()),
    ]
    encontrado, veces = tc.buscar_evento(lineas, CID)
    assert veces == 2
    assert encontrado["confidence"] == 0.9393, "se usa la ultima linea"


def test_id_ausente_en_el_jsonl():
    assert tc.buscar_evento([json.dumps(evento(capture_id="otro"))], CID) == (None, 0)


def test_linea_que_no_es_json_falla_con_su_numero():
    with pytest.raises(ValueError, match="linea 2"):
        tc.buscar_evento([json.dumps(evento()), "{roto"], CID)


# --- codigo de salida y formato --------------------------------------------------


def test_codigo_de_salida():
    ok = tc.Traza(CID, filas=tc.comparar_campos({"a": evento(), "b": registro()}))
    assert ok.codigo == 0
    mal = tc.Traza(CID, filas=tc.comparar_campos({"a": evento(), "b": registro(confidence=0.1)}))
    assert mal.codigo == 1
    error = tc.Traza(CID, filas=ok.filas, errores=["S3 no responde"])
    assert error.codigo == 2


def test_formato_muestra_valores_completos_y_resultado():
    traza = tc.Traza(
        CID,
        filas=tc.comparar_campos({"dispositivo": evento(), "S3": registro(predicted_class="dog")}),
        detalles=["registro: VersionId v1"],
        avisos=["Se omite el portal"],
    )
    texto = tc.formatear(traza)
    assert "predicted_class" in texto and "NO coincide" in texto
    assert "ca689c4e1478ccca7821dffaba8f07886bd9609a8aa3cec7450d9f875fbd69c0" in texto
    assert "Resultado: HAY DIFERENCIAS (codigo de salida 1)" in texto
    assert "7 de 7 filas comparadas entre dos o mas fuentes" in texto
    assert "Se omite el portal" in texto


# --- portal: credenciales --------------------------------------------------------


def test_sin_credenciales_se_omite_el_portal_y_se_avisa(monkeypatch):
    monkeypatch.delenv("P4_PORTAL_USUARIO", raising=False)
    monkeypatch.delenv("P4_PORTAL_PASSWORD", raising=False)
    traza = tc.Traza(CID)
    args = argparse.Namespace(sin_portal=False, portal=tc.DEFAULT_PORTAL, capture_id=CID)
    assert tc.leer_portal(args, traza) == (None, None)
    assert any("P4_PORTAL_PASSWORD" in aviso for aviso in traza.avisos)


# --- main de punta a punta (S3 y portal sustituidos) -----------------------------


def test_main_de_punta_a_punta(tmp_path, monkeypatch):
    events = tmp_path / "events.jsonl"
    events.write_text(json.dumps(evento()) + "\n", encoding="utf-8")
    (tmp_path / "capturas").mkdir()
    (tmp_path / "capturas" / "edge01-44e6a9b3.jpg").write_bytes(FOTO)
    salida = tmp_path / "evidencia" / "traza.txt"

    monkeypatch.setattr(tc, "leer_s3", lambda args, traza: (registro(), SHA_FOTO, SHA_FOTO))
    monkeypatch.setattr(tc, "leer_portal", lambda args, traza: (registro(), SHA_FOTO))
    codigo = tc.main(
        [
            "--capture-id",
            CID,
            "--events",
            str(events),
            "--fotos-dir",
            str(tmp_path / "capturas"),
            "--salida",
            str(salida),
        ]
    )
    assert codigo == 0
    texto = salida.read_text(encoding="utf-8")
    assert "Resultado: TODO COINCIDE" in texto
    assert "dispositivo (foto local)" in texto


def test_main_detecta_imagen_distinta(tmp_path, monkeypatch):
    events = tmp_path / "events.jsonl"
    events.write_text(json.dumps(evento()) + "\n", encoding="utf-8")
    foto = tmp_path / "otra.jpg"
    foto.write_bytes(b"otra foto")
    monkeypatch.setattr(tc, "leer_s3", lambda args, traza: (registro(), SHA_FOTO, SHA_FOTO))
    monkeypatch.setattr(tc, "leer_portal", lambda args, traza: (None, None))
    assert tc.main(["--capture-id", CID, "--events", str(events), "--foto", str(foto)]) == 1


def test_main_sin_registro_en_s3_sale_con_2(tmp_path, monkeypatch):
    def sin_registro(args, traza):
        traza.errores.append("No hay registro en S3")
        return None, None, None

    monkeypatch.setattr(tc, "leer_s3", sin_registro)
    monkeypatch.setattr(tc, "leer_portal", lambda args, traza: (None, None))
    assert tc.main(["--capture-id", CID]) == 2
