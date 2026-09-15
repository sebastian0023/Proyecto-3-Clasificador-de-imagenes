# Dataset Quality & Versioning

Plataforma de **calidad y versionado** para el dataset de detección de objetos
(formato COCO) producido por el proyecto de anotación (MP1).

Analiza el dataset crudo, aplica una **compuerta de calidad** que puede bloquear
la publicación, genera los splits estratificados y publica versiones inmutables
y content-addressed hacia MinIO en local / S3 en producción.

Stack: Python 3.12 · FastAPI · pydantic-settings · SQLAlchemy sobre MariaDB ·
MinIO (S3-compatible) · Docker Compose · Ruff · pytest.

---

## Requisitos previos

- **Docker Desktop** (Compose v2) instalado y corriendo.
- **Python 3.12** en el host, únicamente para lanzar el comando de arranque.
  `scripts/up.py` usa solo la librería estándar: no hace falta crear un entorno
  virtual ni instalar dependencias para levantar el proyecto.

No se necesita nada más. Sin Node, sin `pip install` previo, sin pasos manuales.

## Puesta en marcha desde cero

Desde un clon limpio, estos son **todos** los comandos necesarios:

```bash
git clone <url-del-repo>
cd dataset-quality
python scripts/up.py
```

`python scripts/up.py` es el punto único de arranque. Orquesta la secuencia
completa sin intervención manual:

1. Si no existe `.env`, lo crea copiando `.env.example`. Los valores por defecto
   funcionan para el entorno local; no se versiona ningún `.env` real.
2. Construye la imagen de la app y levanta los tres servicios —
   **app + MariaDB + MinIO** — esperando a que los tres reporten `healthy`
   (`docker compose up -d --build --wait`).
3. Crea los buckets de MinIO con un job idempotente (`minio-init`).
4. Consulta `/health` y **falla con código distinto de cero** si MariaDB o MinIO
   no responden desde dentro de la app. No basta con que el contenedor exista.
5. Imprime las URLs de trabajo.

> La primera ejecución descarga las imágenes base de Docker y compila la imagen
> de la app; tarda unos minutos. Las siguientes son cuestión de segundos.

Al terminar verás:

```
Entorno listo.

  App / UI          http://localhost:8000
  OpenAPI           http://localhost:8000/docs
  Health            http://localhost:8000/health
  Consola MinIO     http://localhost:9101   (usuario y clave en .env)
```

### Puertos

| Recurso        | URL / puerto             | Variable en `.env`    |
| -------------- | ------------------------ | --------------------- |
| App / UI       | `http://localhost:8000`  | `APP_PORT`            |
| MariaDB        | `localhost:3307`         | `DB_PORT`             |
| MinIO (API)    | `localhost:9100`         | `MINIO_PORT`          |
| MinIO (consola)| `http://localhost:9101`  | `MINIO_CONSOLE_PORT`  |

Los puertos están corridos a propósito respecto al proyecto de anotación
(3306 / 9000 / 9001) para que ambos entornos convivan en la misma máquina.

### Otros comandos

```bash
python scripts/up.py --logs      # al terminar, sigue los logs de la app
python scripts/up.py --no-build  # no reconstruye la imagen (arranque rápido)
python scripts/up.py --fresh     # borra volúmenes y empieza de cero
python scripts/down.py           # apaga y conserva los datos
python scripts/down.py --volumes # apaga y borra los datos (pide confirmación)
```

El código de `src/` está montado en vivo dentro del contenedor: al guardar un
archivo, uvicorn recarga solo.

---

## Configuración: cero credenciales en el código

Toda la configuración entra por variables de entorno, y en local esas variables
salen de un único archivo `.env`. Hay tres capas que lo hacen cumplir, y ninguna
es una promesa: las tres fallan ruidosamente.

### 1. `src/dataset_quality/settings.py` — pydantic-settings

Un modelo `BaseSettings` con tipos estrictos. Las credenciales son `SecretStr` y
**no tienen valor por defecto**. Si falta una, el proceso aborta al arrancar:

```
pydantic_core._pydantic_core.ValidationError: 1 validation error for Settings
db_password
  Field required [type=missing, ...]
```

`SecretStr` además impide el filtrado accidental: la contraseña no aparece en
`repr()`, ni en los logs, ni en el endpoint `/api/config`. Hay una prueba que lo
verifica (`tests/test_settings.py`).

### 2. `docker-compose.yml` — sin valores por defecto

Usa la sintaxis `${VAR:?mensaje}`. Si la variable no está en `.env`, Compose se
niega a arrancar en vez de levantar la base de datos con una contraseña que
alguien podría adivinar:

```
$ docker compose config
error while interpolating services.mariadb.environment.MARIADB_PASSWORD:
required variable DB_PASSWORD is missing a value: falta DB_PASSWORD en .env
```

### 3. `.gitignore` y `.dockerignore`

`.env` está en ambos: nunca se commitea ni entra en la imagen. Lo único
versionado es la plantilla `.env.example`, con valores de desarrollo.

### La excepción, y por qué no es un secreto

Compose fija a mano cuatro variables para el servicio `app`:

```yaml
DB_HOST: mariadb
DB_PORT: "3306"
MINIO_ENDPOINT: minio
MINIO_PORT: "9000"
```

Son **topología de red interna** de Docker, no configuración secreta: dentro de
la red de Compose los servicios se llaman por su nombre. Gracias a eso, `.env`
puede seguir apuntando a `localhost` para cuando corras la app fuera de Docker.

`GET /api/config` devuelve la configuración efectiva **sin secretos**, útil para
verificar contra qué base y qué bucket está trabajando el entorno.

---

---

## Traer el dataset del Proyecto 1

El portal de anotacion expone su dataset por HTTP. Este script lo descarga a
`data/raw/` — que es donde el pipeline lo busca — y de paso **verifica el
minimo del curso**: al menos 300 imagenes distintas en al menos 2 clases.

```bash
# El Proyecto 1 tiene que estar levantado (npm run up en su repositorio)
python scripts/export_from_mp1.py
```

| Opcion | Para que |
| ------ | -------- |
| `--check-only` | Solo consulta el conteo por clase; no descarga nada. Rapido, para el seguimiento diario. |
| `--strict` | Sale con codigo 1 si el minimo no se cumple. Util en CI. |
| `--fresh` | Borra las imagenes locales antes de descargar. |
| `--base-url URL` | Apunta a otro host (por defecto, `MP1_BASE_URL` del `.env`). |

La descarga es **reanudable**: si se corta, vuelve a correr el script y retoma
donde se quedo en vez de empezar de cero.

### Por que por HTTP y no leyendo su base de datos

`GET /api/coco/export` es el contrato publico que el propio README del
Proyecto 1 declara como entregable. Usarlo evita acoplar este proyecto a su
esquema de Drizzle y evita necesitar sus credenciales de MariaDB o MinIO. La
llave que une las dos mitades es el `id`: el de `coco.images[]` es el mismo que
el de `GET /api/images/{id}/file`.

### Por que la descarga vive fuera del pipeline

Ocurre **una vez**. El pipeline solo lee `data/raw/`, asi que sigue siendo
reproducible aunque el Proyecto 1 no este corriendo — que es exactamente la
situacion del evaluador. Una etapa que hiciera una peticion HTTP dejaria de ser
determinista.

### Sobre el conteo

Se cuentan **imagenes distintas que contienen al menos una caja de esa clase**,
no cajas: una foto con siete coches aporta una imagen a `car`, no siete. Y es
un conteo *antes* de colapsar casi-duplicados; el numero que vale para la
evaluacion es el de despues, que dara el analizador de duplicados.


## Ingerir el dataset (Tier 1)

Una vez los datos estan en `data/raw/`, este comando los reparte entre los dos
almacenes:

```bash
dq ingest
```

```
data/raw/annotations.coco.json ──► CocoDataset (Pydantic)
                                        │
                      ┌─────────────────┴─────────────────┐
                      ▼                                   ▼
        MinIO: los bytes de cada imagen       MariaDB: metadatos y cajas
        bucket `dataset-images`,              categories / images / annotations
        llave `raw/<archivo>`
```

### Por que las imagenes no van a MariaDB

Los metadatos se consultan y se agregan (*¿cuantas cajas de clase `dog` hay?*);
eso en SQL es una linea. Los binarios solo se guardan y se sirven, y para eso
una base de datos es el peor sitio: meter 877 JPEGs en columnas hace que las
copias de seguridad tarden horas y obliga a pasar cada imagen entera por el
servidor para mostrarla.

El reparto es el estandar: **los metadatos a la base, los bytes al almacen de
objetos**. En `images.storage_key` queda la llave del objeto; el binario nunca
entra en una columna. Hay una prueba que lo verifica (`test_ingest.py`).

En local ese almacen es MinIO; en produccion es S3. El codigo es el mismo — solo
cambia el endpoint.

### Tres propiedades del Tier 1

**Valida antes de escribir.** El COCO pasa entero por los modelos Pydantic del
Frente 2. Un archivo roto se rechaza nombrando el campo:

```
data/raw/annotations.coco.json: 1 error(es) de validacion
  - images.0.width: Input should be greater than 0 (recibido: 0)
```

**Sube antes de registrar.** Los objetos van primero y las filas despues, de
modo que nunca queda una fila apuntando a un objeto que no existe.

**Es idempotente.** Correrlo dos veces deja el mismo estado: las imagenes que ya
estan en MinIO no se vuelven a subir (se comparan por tamano) y las tablas se
redefinen en vez de acumular.

### Verificar

```bash
# filas en MariaDB
docker compose exec mariadb sh -c   'mariadb -u"$MARIADB_USER" -p"$MARIADB_PASSWORD" "$MARIADB_DATABASE" -e    "SELECT COUNT(*) FROM images; SELECT COUNT(*) FROM annotations;"'

# objetos en MinIO
docker compose exec minio sh -c   'mc alias set l http://localhost:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" &&    mc du l/dataset-images'
```


## Generar los splits (Tier 4)

Una vez el dataset esta en `data/raw/` y la compuerta de calidad (Tier 3) pasa,
este comando reparte las imagenes en train/val/test:

```bash
dq gate     # Tier 3 — tiene que pasar antes
dq split    # Tier 4 — splits.json
```

```
reports/quality.json ──► ¿status == pass? ──► CocoDataset + pHash (Frente 3)
                                                        │
                                          agrupa casi-duplicados en unidades
                                                        │
                                       reparte por estrato (semilla + largest
                                       remainder) ──► reports/splits.json
```

### Por que la compuerta bloquea a `dq split`

`quality.json` en `fail` significa que la compuerta del Tier 3 detecto algo
que no debe publicarse (por ejemplo, demasiados duplicados). Generar splits
sobre ese dataset produciria un `splits.json` que habria que tirar en cuanto
se arreglara el problema. `dq split` lee `reports/quality.json` y se niega a
correr si no existe o si `status == "fail"`, con el mismo espiritu que el
docstring de la compuerta promete: *"la etapa siguiente del pipeline no se
ejecuta"*. `--force` salta la comprobacion a proposito, dejando constancia en
la terminal — util para iterar en local sin un dataset completo todavia.

### Por que se agrupan los casi-duplicados en vez de descartarlos

La unidad que reparte `dq split` no es la imagen: es el **grupo de
casi-duplicados** que ya detecta el pHash del Frente 3
(`analyzers.duplicates.duplicate_groups`, componentes conexas sobre la
distancia de Hamming). Un grupo entero viaja a un solo split, lo que hace la
fuga estructuralmente imposible en vez de ser un chequeo que alguien podria
olvidar. Descartar las copias en vez de agruparlas era la alternativa mas
simple, pero reduce el dataset y puede tirar el minimo de 300 imagenes por
clase que exige la compuerta M3 — agrupar no pierde ninguna imagen.

### Por que se estratifica por la clase minoritaria de la imagen

Una imagen puede tener cajas de varias clases. Usar la clase **menos
frecuente** de cada imagen como etiqueta de estratificacion (en vez de la mas
frecuente, o de la combinacion completa) protege a las clases raras: son las
que mas se perjudican si quedan mal representadas en val/test, y una clase
con pocas imagenes en todo el dataset no puede permitirse perderlas todas en
train.

### Verificar

```bash
# El artefacto valida contra su propio contrato congelado
python -c "
from pathlib import Path
from dataset_quality.models.splits import SplitsManifest
m = SplitsManifest.model_validate_json(Path('reports/splits.json').read_text())
print(m.counts, 'total:', len(m.assignments))
"

# Reproducibilidad: misma semilla, mismo reparto
dq split --out /tmp/a.json && dq split --out /tmp/b.json
diff <(python -c "import json;d=json.load(open('/tmp/a.json'));d.pop('generated_at');print(d)") \
     <(python -c "import json;d=json.load(open('/tmp/b.json'));d.pop('generated_at');print(d)")
```

## Versionar y publicar (Tier 5, Frente 6)

Con la compuerta en `pass` y los splits generados, `dq release` empaqueta el
dataset y sus dos reportes en un artefacto inmutable, lo sube al almacen de
objetos y registra la version:

```bash
dq gate && dq split   # tienen que pasar antes
dq release            # Tier 5 — versions.json + s3://dataset-releases/...
```

```
quality.json + splits.json + annotations.coco.json
                    │
      tar + zstandard, metadata deterministica
      (mtime fijo, orden fijo de miembros)
                    │
                    ▼
      s3://dataset-releases/<version>/dataset.tar.zst
                    │
                    ▼
              reports/versions.json  (registro acumulado)
```

### El pipeline por etapas: `dvc.yaml`

Las cuatro etapas puras del pipeline — `analyze`, `gate`, `split`, `release` —
estan declaradas en `dvc.yaml` con sus `deps`/`outs` exactos, para que
`dvc repro` reejecute solo lo que cambio:

```bash
dvc dag       # dibuja el grafo: gate -> split -> release (analyze es aparte)
dvc repro     # corre lo que haga falta; si nada cambio, no hace nada
```

`gate` depende de `data/raw/` y `quality.yaml`; `split` depende ademas de
`reports/quality.json`, así que **DVC no genera splits si la compuerta no
paso** — el mismo candado que ya aplica `dq split` por su cuenta, ahora
tambien expresado en el grafo. `release` depende de `quality.json` y
`splits.json`.

### Por que `dq ingest` no es una etapa de `dvc.yaml`

`dvc repro` tiene que ser una funcion determinista de archivos a archivos.
La ingesta escribe en MinIO y MariaDB, no deja un artefacto en disco que DVC
pueda cachear, y exigiria Docker levantado para reproducir el pipeline. Queda
como paso manual previo — igual que `export_from_mp1.py`, y por la misma
razon: ocurre una vez, no en cada corrida del pipeline.

### Que va a Git y que no

| Se versiona en Git | Vive solo en el remote (`dvc push`) |
| --- | --- |
| `dvc.yaml`, `dvc.lock` | `data/raw/` (el dataset crudo) |
| `reports/*.json` (`cache: false`: texto pequeño y diferenciable) | `reports/releases/<version>/dataset.tar.zst` |
| `.dvc/config` (URLs de los remotes, sin credenciales) | — |
| `.dvc/config.local` **nunca** — esta en `.dvc/.gitignore` | credenciales de `dev`/`prod` |

### Remotes DEV/PROD

`dev` (MinIO local) es el remote por defecto; `prod` (S3 real) esta declarado
pero sin credenciales hasta que exista un bucket de produccion:

```bash
cat .dvc/config              # solo URLs, versionado, sin secretos
python scripts/dvc_remote.py # escribe .dvc/config.local desde .env (MinIO)
dvc push                     # sube al remote activo (dev)
dvc push -r prod              # cuando 'prod' tenga sus propias credenciales
```

El mismo dataset da el mismo `dataset_fingerprint` sin importar a que remote
se suba: el archivo se arma con metadata deterministica (mtime fijo a epoca
0, miembros en orden fijo), asi que el contenido —no el destino— es lo unico
que determina el hash.

### Auto-incremento de version

`dq release` sube el patch de la ultima version publicada (`0.1.0 -> 0.1.1`);
`--minor`/`--major` suben esa parte, y `--version X.Y.Z` fuerza un valor.
Sin historial previo arranca en `0.1.0`.

### Verificar

```bash
# El registro valida contra su propio contrato congelado
python -c "
from pathlib import Path
from dataset_quality.models.versions import VersionsManifest
m = VersionsManifest.model_validate_json(Path('reports/versions.json').read_text())
last = m.versions[-1]
print(last.version, last.storage_uri, last.quality_status)
"

# El release esta de verdad en el bucket
docker compose exec minio sh -c \
  'mc alias set l http://localhost:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" && mc ls -r l/dataset-releases'

# Reproducibilidad del grafo: sin cambios, dvc no reejecuta nada
dvc repro     # "Stage ... didn't change, skipping"

# --dry-run arma el archivo y calcula sus huellas sin subir nada
dq release --dry-run
```

## Verificación

| Comando | Qué verifica |
| ------- | ------------ |
| `python scripts/check.py` (o `make check`) | **Validación diaria (<30s, Frente 10)**: Ruff lint + format, pytest, Terraform validate e higiene de Git/secretos en un solo paso. |
| `python scripts/up.py` | App + MariaDB + MinIO arriba, buckets creados y `/health` en OK. |
| `curl localhost:8000/health` | `200` con ambos checks en `up`; `503` si alguno está caído. |
| `curl localhost:8000/api/config` | Configuración efectiva sin credenciales. |
| `pytest` | Suite completa (configuración y health). |
| `ruff check . && ruff format --check .` | Lint y formato en cero. |

### Comprobar que la validación de secretos funciona

```bash
grep -v '^DB_PASSWORD=' .env > .env.tmp && mv .env .env.bak && mv .env.tmp .env
docker compose config          # debe fallar nombrando DB_PASSWORD
mv .env.bak .env               # restaurar
```

## Desarrollo en el host (opcional)

Para ejecutar pruebas y linter fuera de Docker:

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # Linux / macOS
pip install -e ".[dev]"

pytest
ruff check . && ruff format .
```

Las pruebas no tocan Docker ni la red: `tests/conftest.py` inyecta un entorno
completo y `/health` se prueba con dobles de las dependencias.

Para usar `dvc` (correr el pipeline, `dvc push`/`pull`), instala tambien el
extra `pipeline`: `pip install -e ".[dev,pipeline]"`. No hace falta para
`pytest`/`ruff`, solo para orquestar el grafo de `dvc.yaml`.

## Integración continua

`.github/workflows/ci.yml` corre en cada push y **falla el build** si algo no
cumple. Dos jobs:

- **Ruff + pytest** — lint, formato y suite de pruebas.
- **Arranque desde cero** — clona y ejecuta `python scripts/up.py` en un runner
  limpio. Es la misma comprobación que hace el evaluador al clonar el repo.

---

## Estructura

```
.
├── docker-compose.yml          # app + MariaDB + MinIO + minio-init
├── docker/Dockerfile           # imagen de la app (python:3.12-slim, usuario no root)
├── .env.example                # plantilla: el ÚNICO lugar con credenciales
├── .github/workflows/ci.yml    # lint, pruebas, arranque desde cero y grafo de DVC
├── dvc.yaml                     # pipeline por etapas (Frente 6): analyze, gate, split, release
├── dvc.lock                      # hashes de deps/outs de cada etapa — se versiona en Git
├── .dvc/config                   # URLs de los remotes dev (MinIO) y prod (S3); sin credenciales
├── scripts/
│   ├── up.py                   # el comando: levanta y verifica todo
│   ├── down.py                  # apaga el entorno
│   └── dvc_remote.py             # escribe .dvc/config.local (credenciales) desde .env
├── quality.yaml                 # umbrales de calidad (Frente 4) y parametros de splits (Frente 5)
├── src/dataset_quality/
│   ├── settings.py             # pydantic-settings: la frontera con el entorno
│   ├── db.py                   # engine SQLAlchemy -> MariaDB
│   ├── storage.py              # cliente S3 -> MinIO
│   ├── tables.py                # tablas SQLAlchemy: images, annotations, categories, splits, dataset_versions
│   ├── cli.py                   # subcomandos `dq`: ingest, analyze, gate, split, release, init-db
│   ├── main.py                  # FastAPI: /, /health, /api/config, /docs
│   ├── analyzers/                # Frente 3: los cinco analizadores + descriptiva
│   │   └── duplicates.py        # pHash, distancia de Hamming, grupos de casi-duplicados
│   ├── tiers/                    # un modulo por etapa del pipeline
│   │   ├── ingest.py             # Tier 1 — COCO -> MinIO + MariaDB (fuera del grafo DVC)
│   │   ├── gate.py               # Tier 3 — compuerta de calidad -> quality.json
│   │   ├── splits.py             # Tier 4 — splits estratificados -> splits.json
│   │   └── release.py            # Tier 5 — empaqueta y publica -> versions.json (Frente 6)
│   ├── models/                 # Pydantic v2: COCO, quality.yaml y los 3 contratos de salida
│   │   ├── coco.py             # dataset COCO crudo (entrada)
│   │   ├── quality.py          # quality.yaml (entrada) y quality.json (salida)
│   │   ├── splits.py           # splits.json (salida, contrato congelado)
│   │   ├── versions.py         # versions.json (salida, contrato congelado)
│   │   └── errors.py           # ValidationError -> mensaje que nombra el campo
│   └── static/index.html       # landing con el estado de la infraestructura
└── tests/                      # pytest
    └── fixtures/                # ejemplos COCO y los 3 golden files congelados
```

## Contratos de datos (Frente 2)

Los modelos de `src/dataset_quality/models/` son la frontera tipada del proyecto:
todo lo que entra o sale de la plataforma de calidad se valida contra ellos, y
un documento inválido se rechaza nombrando el campo exacto que falló (no un
traceback genérico de Pydantic).

| Archivo | Dirección | Modelo principal |
| --- | --- | --- |
| dataset COCO crudo | entrada | `models.coco.CocoDataset` |
| `quality.yaml` | entrada | `models.quality.QualityConfig` |
| `quality.json` | salida — **contrato congelado** | `models.quality.QualityReport` |
| `splits.json` | salida — **contrato congelado** | `models.splits.SplitsManifest` |
| `versions.json` | salida — **contrato congelado** | `models.versions.VersionsManifest` |

Los tres contratos de salida están en `schema_version=1` y protegidos por
`tests/test_contratos_congelados.py`, que hace un round-trip contra los
ejemplos de oro en `tests/fixtures/`. Cambiar su forma sin subir la versión y
actualizar esos fixtures rompe la prueba a propósito: es lo que permite que
los Frentes 3, 4, 5, 7 y 8 desarrollen en paralelo contra un contrato estable.


## Estado y siguiente paso

**Frente 1 (Arquitectura y entorno) — cerrado.** Un comando levanta app +
MariaDB + MinIO, la configuración va por pydantic-settings y no hay ninguna
credencial en el código.

**Frente 2 (Validación Pydantic) — cerrado.** Modelos Pydantic v2 del COCO, de
`quality.yaml` y los tres contratos de salida (`quality.json`, `splits.json`,
`versions.json`) congelados con ejemplos escritos a mano.

**Frente 3 (Analizadores de calidad) — cerrado.** Los cinco analizadores
(objetos pequeños, desbalance de clases, duplicados por pHash, cajas
degeneradas, sesgo espacial) corren sobre `CocoDataset` y devuelven
`CheckResult`; `dq analyze` los orquesta.

**Frente 4 (Compuerta de calidad) — cerrado.** `dq gate` evalúa la política de
`quality.yaml`, escribe `quality.json` y **devuelve el exit code real**: un
`fail` con `severity=error` detiene el pipeline de verdad.

**Frente 5 (Splits estratificados) — cerrado.** `dq split` reparte
train/val/test estratificando por la clase minoritaria de cada imagen, agrupa
los casi-duplicados del pHash (Frente 3) en una sola unidad para garantizar
cero fuga, reparte por semilla con *largest remainder*, y se niega a correr
si la compuerta de calidad (Frente 4) está en `fail` — salvo `--force`.

**Frente 6 (Versionado con DVC) — cerrado.** `dvc.yaml` declara el pipeline
por etapas (`analyze`, `gate`, `split`, `release`); `dq release` empaqueta el
dataset y sus reportes en un `.tar.zst` determinístico, lo publica en
`s3://dataset-releases/<version>/` y registra la entrada en `versions.json`
— el tercer contrato congelado, ya con productor. Dos remotes (`dev` hacia
MinIO local, `prod` hacia S3) comparten el mismo content hash sin importar
a cuál se suba.

**Frente 9 (Infraestructura — Terraform) — cerrado.** 3 módulos por capa:
red con VPC Endpoint para S3, almacenamiento S3 versionado con SSE-S3 y
bloqueo público, e IAM OIDC sin claves estáticas para GitHub Actions.
Validación automática integrada en CI.

**Frente 10 (Ruff, pytest y CI) — cerrado.** Lint en cero (`ruff check`),
formato estricto (`ruff format`), suite de pruebas con verificación de
mutación (Red→Green) y comando único de validación rápida en menos de 5
segundos (`scripts/check.py` / `make check`). Pipeline de CI fail-fast sin
`continue-on-error`.


Lo que sigue, en el orden en que desbloquea:

1. **Migraciones** — Alembic para versionar el esquema de `tables.py`
   (`quality_reports` y `check_results` siguen sin tabla; `splits` y
   `dataset_versions` ya existen).
2. **Frente 7** — la app web que consulta `quality.json`, `splits.json` y
   `versions.json`.
3. **Frente 8** — el Copilot que interpreta los reportes.
