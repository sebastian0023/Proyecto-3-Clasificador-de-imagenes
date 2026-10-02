# Proyecto 3 — Clasificador de imágenes integrado al portal

Clasificador multiclase de un objeto por imagen, entrenado con recortes de las cajas COCO del release aprobado del Proyecto 2 e integrado en el mismo portal.

| Carpeta | Qué es |
|---|---|
| `Proyecto1/` | Portal de anotación (imágenes, categorías y cajas COCO). |
| `Proyecto2/` | Portal de calidad y versionado del dataset (compuerta, releases con DVC). Es la base del stack de P3. |
| `Proyecto3/` | Worker de entrenamiento, modelo e inferencia (`src/p3/`), pruebas y documentación (`docs/`). |

## Requisitos

- Docker Desktop (Compose v2) corriendo.
- Python 3.12 en el host. En Windows, si `python` abre la Microsoft Store, usa `py -3.12` en su lugar.

## Arranque desde un clon limpio

```bash
git clone <url-del-repo> Proyecto-3-Clasificador-de-imagenes
cd Proyecto-3-Clasificador-de-imagenes/Proyecto2
python scripts/up.py
```

`scripts/up.py` crea `.env` desde `.env.example` si no existe, construye las imágenes y levanta todos los servicios esperando a que estén sanos. Falla con código distinto de cero si la app, MariaDB, MinIO o MLflow no responden.

| Servicio | URL |
|---|---|
| Portal (UI + API) | http://localhost:8000 |
| OpenAPI | http://localhost:8000/docs |
| MLflow | http://localhost:5000 |
| Consola MinIO | http://localhost:9101 |

El worker de entrenamiento (`p3-worker`) no publica puertos: toma los trabajos de la cola en MariaDB.

Para apagar sin perder datos: `python scripts/down.py` (desde `Proyecto2/`). Los registros y artefactos de MLflow viven en el volumen `mlflow_data` y sobreviven a `down`/`up`.

## Dataset real (release aprobado de P2)

El dataset no está en Git; se recupera con DVC desde S3. Necesitas un perfil de AWS autorizado en `~/.aws` (las llaves nunca se escriben en el repositorio). Desde `Proyecto2/`:

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.lock.txt   # en Linux/macOS: .venv/bin/pip
.venv/Scripts/dvc remote modify --local prod profile <tu-perfil>
.venv/Scripts/dvc pull -r prod data/raw.dvc
.venv/Scripts/dvc status data/raw.dvc                 # "Data and pipelines are up to date."
```

El release de origen y su verificación están en [`Proyecto3/docs/decisiones.md`](Proyecto3/docs/decisiones.md).

## Manifiesto, recortes y corridas de MLflow (Proyecto 3)

Desde `Proyecto3/`, con el mismo perfil de AWS (usa el `dvc` del venv de Proyecto2):

```bash
../Proyecto2/.venv/Scripts/dvc remote modify --local prod profile <tu-perfil>
../Proyecto2/.venv/Scripts/dvc pull data/manifests/m-0.1.3-s42-1.dvc mlflow_snapshot.dvc
```

Nombra los dos punteros: un `dvc pull` sin argumentos trae el snapshot de MLflow pero no el manifiesto congelado.

Los recortes se regeneran desde el release (idénticos byte a byte, ver `Proyecto3/docs/verificacion_recortes.md`). Desde `Proyecto2/`:

```bash
PYTHONPATH="../Proyecto3/src;src" .venv/Scripts/python ../Proyecto3/scripts/generate_crops.py --release 0.1.3 --profile <tu-perfil>
```

Después de `dvc pull` y de los recortes, vuelve a correr `python scripts/up.py` desde `Proyecto2/`: carga las 12 corridas del barrido en MLflow (`http://localhost:5000`) aunque el primer `up.py` lo haya dejado vacío, y reinicia MLflow para que las lea. Si MLflow ya tiene corridas, no las toca.

Si la máquina tiene GPU NVIDIA (Docker Desktop con WSL2 o NVIDIA Container Toolkit), `up.py` se la asigna al worker; si no, entrena en CPU. `P3_GPU=0` o `P3_GPU=1` fuerzan la elección.

## Comprobar el worker

```bash
curl -X POST http://localhost:8000/api/p3/training/jobs \
  -H "Content-Type: application/json" \
  -d '{"kind": "dummy", "config": {"steps": 5, "seconds": 1}}'
curl http://localhost:8000/api/p3/training/jobs/<job_id>
```

El `POST` responde `202` con el `job_id` sin ejecutar nada; el `GET` muestra estado, progreso, logs y error, que persisten al reiniciar.

### Entrenamiento corto (sin GPU)

Para comprobar un entrenamiento real en pocos segundos, en **Training** elige el release `0.1.3`, pulsa *Generar manifiesto 70/20/10* y lanza con esta configuración:

| experiment | optimizer | batch_size | max_epochs | learning_rate | image_size | hidden_layers | dropout | seed |
|---|---|---|---|---|---|---|---|---|
| `p3-pruebas` | `adamw` | 64 | 1 | 0.001 | 64 | 128 | 0.2 | 42 |

En CPU termina en ~30 s (medido: 28 s, `val_acc` 0.81). La corrida queda en el experimento `p3-pruebas` de MLflow; `p3-clasificador` conserva solo las 12 corridas del barrido. Recargar la página durante el trabajo conserva su estado y sus logs.

## Pruebas de Proyecto 3

Desde `Proyecto3/`:

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.lock.txt
.venv/Scripts/pip install --no-deps -e .
.venv/Scripts/ruff check . && .venv/Scripts/ruff format --check .
.venv/Scripts/pytest
```

## Documentación

- [`Proyecto3/AGENTS.md`](Proyecto3/AGENTS.md): contexto y reglas del equipo.
- [`Proyecto3/docs/PLAN.md`](Proyecto3/docs/PLAN.md): roles, cronograma y controles.
- [`Proyecto3/docs/fases/`](Proyecto3/docs/fases/): una guía por fase con su registro de avance.
- [`Proyecto3/docs/inventario.md`](Proyecto3/docs/inventario.md): dónde está cada pieza de P1 y P2.
