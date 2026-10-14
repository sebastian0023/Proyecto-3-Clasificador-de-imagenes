"""Sigue una captura por ID en dispositivo, AWS (S3) y portal, y compara lo que dice cada uno (F6).

Solo lee: `head-object`, `get-object` y `list-objects-v2` en S3 (perfil de AWS) y `GET` en el
portal desplegado. Nunca escribe en S3 ni en el portal.

Fuentes:
- dispositivo: la linea del `events.jsonl` de la Pi con ese `capture_id` (`--events`) y, si se da,
  la foto local (`--foto`, o `--fotos-dir` + el `image_ref` del evento);
- S3: el registro `edge-captures/events/{id}.json` y la imagen `edge-captures/images/{id}.jpg`
  (SHA-256 de sus metadatos y de la descarga);
- portal: `GET /api/p4/captures/{id}` y `/image` con basic_auth. Usuario y contrasena salen de
  `P4_PORTAL_USUARIO` y `P4_PORTAL_PASSWORD` (cargadas con `Read-Host -AsSecureString`); si
  faltan, esa parte se omite y se avisa. Nunca se imprimen.

Codigo de salida: 0 si todo lo comparado coincide; 1 si algo NO coincide; 2 si falta la captura en
S3 o hubo un error de lectura.

    python scripts/trazar_captura.py --capture-id <id> --events events.jsonl --fotos-dir capturas
        --salida C:/MLOps_Project_Four/evidencia_f6/traza_<id>.txt
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Campos del evento que deben ser identicos en las tres fuentes (contrato schema_version 1).
CAMPOS = (
    "capture_id",
    "predicted_class",
    "confidence",
    "model_version",
    "model_sha256",
    "captured_at",
    "image_sha256",
)
FALTA = "(falta el campo)"
COINCIDE = "coincide"
NO_COINCIDE = "NO coincide"
SIN_COMPARAR = "sin comparar (una sola fuente)"

DEFAULT_PORTAL = "https://174-129-84-80.sslip.io"
DEFAULT_BUCKET = "dataset-quality-releases-750702272375"
DEFAULT_PREFIX = "edge-captures/"


@dataclass
class Fila:
    campo: str
    valores: dict[str, Any]
    estado: str


@dataclass
class Traza:
    capture_id: str
    filas: list[Fila] = field(default_factory=list)
    detalles: list[str] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)
    errores: list[str] = field(default_factory=list)

    @property
    def codigo(self) -> int:
        if self.errores:
            return 2
        return 1 if any(fila.estado == NO_COINCIDE for fila in self.filas) else 0


# --- comparacion (funciones puras: las pruebas no tocan AWS) -----------------------


def _estado(valores: dict[str, Any]) -> str:
    if len(valores) < 2:
        return SIN_COMPARAR
    distintos = {json.dumps(valor, sort_keys=True) for valor in valores.values()}
    return COINCIDE if len(distintos) == 1 else NO_COINCIDE


def comparar_campos(fuentes: dict[str, dict[str, Any] | None]) -> list[Fila]:
    """Una fila por campo del contrato; solo cuentan las fuentes presentes (no `None`).

    Un campo ausente en una fuente presente cuenta como valor distinto (`FALTA`).
    """
    presentes = {nombre: registro for nombre, registro in fuentes.items() if registro is not None}
    filas = []
    for campo in CAMPOS:
        valores = {nombre: registro.get(campo, FALTA) for nombre, registro in presentes.items()}
        filas.append(Fila(campo, valores, _estado(valores)))
    return filas


def comparar_imagen(hashes: dict[str, str | None]) -> Fila:
    """El SHA-256 de la foto en cada lugar donde se pudo calcular u obtener."""
    valores = {nombre: valor for nombre, valor in hashes.items() if valor is not None}
    return Fila("SHA-256 de la imagen", valores, _estado(valores))


def buscar_evento(lineas: list[str], capture_id: str) -> tuple[dict[str, Any] | None, int]:
    """(ultima linea del `events.jsonl` con ese ID, cuantas lineas lo tienen)."""
    encontrados = []
    for numero, linea in enumerate(lineas, start=1):
        if not linea.strip():
            continue
        try:
            evento = json.loads(linea)
        except json.JSONDecodeError as error:
            raise ValueError(f"linea {numero} del events.jsonl no es JSON: {error.msg}") from error
        if isinstance(evento, dict) and evento.get("capture_id") == capture_id:
            encontrados.append(evento)
    return (encontrados[-1] if encontrados else None), len(encontrados)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def formatear(traza: Traza) -> str:
    """Tabla de texto: una fila por (campo, fuente) y el resultado en la primera de cada campo."""
    filas_texto = []
    for fila in traza.filas:
        for indice, (fuente, valor) in enumerate(fila.valores.items()):
            filas_texto.append(
                (
                    fila.campo if indice == 0 else "",
                    fuente,
                    valor if isinstance(valor, str) else json.dumps(valor),
                    fila.estado if indice == 0 else "",
                )
            )
        if not fila.valores:
            filas_texto.append((fila.campo, "-", "(sin fuentes)", fila.estado))
    anchos = [
        max(len(titulo), *(len(f[i]) for f in filas_texto)) if filas_texto else len(titulo)
        for i, titulo in enumerate(("campo", "fuente", "valor", "resultado"))
    ]
    linea = " | ".join

    def fmt(cols: tuple[str, ...]) -> str:
        return linea(c.ljust(anchos[i]) for i, c in enumerate(cols)).rstrip()

    salida = [
        f"Traza de la captura {traza.capture_id}",
        f"Generada: {datetime.now(UTC).isoformat(timespec='seconds')}",
        "",
        fmt(("campo", "fuente", "valor", "resultado")),
        "-+-".join("-" * ancho for ancho in anchos),
    ]
    anterior = None
    for cols in filas_texto:
        if cols[0] and anterior is not None:
            salida.append("-+-".join("-" * ancho for ancho in anchos))
        salida.append(fmt(cols))
        anterior = cols
    if traza.detalles:
        salida += ["", "Detalles:"] + [f"  - {d}" for d in traza.detalles]
    if traza.avisos:
        salida += ["", "Avisos:"] + [f"  - {a}" for a in traza.avisos]
    if traza.errores:
        salida += ["", "Errores:"] + [f"  - {e}" for e in traza.errores]
    resumen = {0: "TODO COINCIDE", 1: "HAY DIFERENCIAS", 2: "ERROR AL LEER"}[traza.codigo]
    # "Coincide" solo vale para lo que se comparo entre dos o mas fuentes: se dice cuanto fue.
    comparadas = sum(1 for fila in traza.filas if fila.estado != SIN_COMPARAR)
    salida += [
        "",
        f"Resultado: {resumen} (codigo de salida {traza.codigo}); "
        f"{comparadas} de {len(traza.filas)} filas comparadas entre dos o mas fuentes",
    ]
    return "\n".join(salida) + "\n"


# --- lectura de las fuentes (solo lectura) ----------------------------------------


def leer_dispositivo(args: argparse.Namespace, traza: Traza) -> tuple[dict | None, str | None]:
    if args.events is None:
        traza.avisos.append("Sin --events: se omite el lado del dispositivo.")
        return None, None
    lineas = Path(args.events).read_text(encoding="utf-8").splitlines()
    evento, veces = buscar_evento(lineas, args.capture_id)
    if evento is None:
        traza.errores.append(f"El capture_id no esta en {args.events}.")
        return None, None
    traza.detalles.append(f"dispositivo: {args.events} ({veces} linea(s) con este ID)")
    if veces > 1:
        traza.avisos.append(f"El ID aparece {veces} veces en el events.jsonl; se usa la ultima.")
    foto = args.foto or (Path(args.fotos_dir) / evento["image_ref"] if args.fotos_dir else None)
    if foto is None:
        traza.avisos.append("Sin --foto ni --fotos-dir: no se compara la foto local.")
        return evento, None
    foto = Path(foto)
    if not foto.is_file():
        traza.errores.append(f"No existe la foto local {foto}.")
        return evento, None
    traza.detalles.append(f"foto local: {foto} ({foto.stat().st_size} bytes)")
    return evento, sha256(foto.read_bytes())


def leer_s3(args: argparse.Namespace, traza: Traza) -> tuple[dict | None, str | None, str | None]:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError

    s3 = boto3.Session(profile_name=args.perfil).client("s3", region_name=args.region)
    llave_registro = f"{args.prefix}events/{args.capture_id}.json"
    llave_imagen = f"{args.prefix}images/{args.capture_id}.jpg"
    try:
        listado = s3.list_objects_v2(
            Bucket=args.bucket, Prefix=f"{args.prefix}events/{args.capture_id}"
        )
        llaves = [o["Key"] for o in listado.get("Contents", [])]
        exactas = [k for k in llaves if k == llave_registro]
        traza.detalles.append(
            f"S3 s3://{args.bucket}/{llave_registro}: {len(exactas)} registro(s) con este ID"
        )
        if not exactas:
            traza.errores.append(f"No hay registro en S3 para {args.capture_id}.")
            return None, None, None
        cabeza_registro = s3.head_object(Bucket=args.bucket, Key=llave_registro)
        registro = json.loads(s3.get_object(Bucket=args.bucket, Key=llave_registro)["Body"].read())
        cabeza_imagen = s3.head_object(Bucket=args.bucket, Key=llave_imagen)
        imagen = s3.get_object(Bucket=args.bucket, Key=llave_imagen)["Body"].read()
    except (ClientError, BotoCoreError) as error:
        traza.errores.append(f"Lectura de S3 fallo: {type(error).__name__}: {error}")
        return None, None, None
    traza.detalles += [
        f"registro: VersionId {cabeza_registro.get('VersionId')}, "
        f"LastModified {cabeza_registro['LastModified'].isoformat()}, "
        f"received_at {registro.get('received_at')}",
        f"imagen s3://{args.bucket}/{llave_imagen}: VersionId {cabeza_imagen.get('VersionId')}, "
        f"{cabeza_imagen['ContentLength']} bytes",
    ]
    return registro, cabeza_imagen.get("Metadata", {}).get("sha256"), sha256(imagen)


def leer_portal(args: argparse.Namespace, traza: Traza) -> tuple[dict | None, str | None]:
    usuario = os.environ.get("P4_PORTAL_USUARIO")
    password = os.environ.get("P4_PORTAL_PASSWORD")
    if args.sin_portal or not usuario or not password:
        traza.avisos.append(
            "Se omite el portal: "
            + (
                "--sin-portal."
                if args.sin_portal
                else "faltan P4_PORTAL_USUARIO o P4_PORTAL_PASSWORD."
            )
        )
        return None, None
    import httpx

    base = f"{args.portal.rstrip('/')}/api/p4/captures/{args.capture_id}"
    try:
        with httpx.Client(auth=(usuario, password), timeout=30) as cliente:
            respuesta = cliente.get(base)
            respuesta_imagen = cliente.get(f"{base}/image")
    except httpx.HTTPError as error:
        traza.errores.append(f"Portal no respondio: {type(error).__name__}")
        return None, None
    traza.detalles.append(
        f"portal {base}: HTTP {respuesta.status_code}; /image: HTTP {respuesta_imagen.status_code}"
    )
    if respuesta.status_code != 200 or respuesta_imagen.status_code != 200:
        traza.errores.append(
            f"El portal respondio {respuesta.status_code} / {respuesta_imagen.status_code}"
            + (" (credenciales de basic_auth rechazadas)" if respuesta.status_code == 401 else "")
        )
        return None, None
    return respuesta.json(), sha256(respuesta_imagen.content)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--capture-id", required=True)
    parser.add_argument("--events", type=Path, help="events.jsonl del dispositivo")
    parser.add_argument("--foto", type=Path, help="foto local del dispositivo")
    parser.add_argument("--fotos-dir", type=Path, help="carpeta de fotos (se usa image_ref)")
    parser.add_argument("--perfil", default="p4-emilio")
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--bucket", default=DEFAULT_BUCKET)
    parser.add_argument("--prefix", default=DEFAULT_PREFIX)
    parser.add_argument("--portal", default=DEFAULT_PORTAL)
    parser.add_argument("--sin-portal", action="store_true")
    parser.add_argument("--salida", type=Path, help="guarda el resultado en este archivo")
    args = parser.parse_args(argv)

    traza = Traza(args.capture_id)
    evento, sha_foto_local = leer_dispositivo(args, traza)
    registro_s3, sha_s3_metadatos, sha_s3_descarga = leer_s3(args, traza)
    registro_portal, sha_portal = leer_portal(args, traza)

    traza.filas = comparar_campos(
        {"dispositivo": evento, "S3": registro_s3, "portal": registro_portal}
    )
    traza.filas.append(
        comparar_imagen(
            {
                "dispositivo (foto local)": sha_foto_local,
                "dispositivo (evento)": evento.get("image_sha256") if evento else None,
                "S3 (metadatos)": sha_s3_metadatos,
                "S3 (descarga)": sha_s3_descarga,
                "portal (descarga)": sha_portal,
            }
        )
    )
    texto = formatear(traza)
    print(texto, end="")
    if args.salida:
        args.salida.parent.mkdir(parents=True, exist_ok=True)
        args.salida.write_text(texto, encoding="utf-8")
    return traza.codigo


if __name__ == "__main__":
    sys.exit(main())
