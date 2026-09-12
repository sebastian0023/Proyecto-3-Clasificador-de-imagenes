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


## Verificación

| Comando | Qué verifica |
| ------- | ------------ |
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
├── .github/workflows/ci.yml    # lint, pruebas y arranque desde cero
├── scripts/
│   ├── up.py                   # el comando: levanta y verifica todo
│   └── down.py                 # apaga el entorno
├── src/dataset_quality/
│   ├── settings.py             # pydantic-settings: la frontera con el entorno
│   ├── db.py                   # engine SQLAlchemy -> MariaDB
│   ├── storage.py              # cliente S3 -> MinIO
│   ├── main.py                 # FastAPI: /, /health, /api/config, /docs
│   └── static/index.html       # landing con el estado de la infraestructura
└── tests/                      # pytest
```

## Estado y siguiente paso

**Frente 1 (Arquitectura y entorno) — cerrado.** Un comando levanta app +
MariaDB + MinIO, la configuración va por pydantic-settings y no hay ninguna
credencial en el código.

Lo que sigue, en el orden en que desbloquea:

1. **Frente 2** — modelos Pydantic v2 del COCO, de `quality.yaml` y del entorno.
2. **Modelo de datos + migraciones** — `dataset_versions`, `quality_reports`,
   `check_results`, `splits`.
3. **Frente 3** — los cinco analizadores (objetos pequeños, desbalance,
   duplicados por pHash, cajas degeneradas, sesgo espacial).
4. **Frente 4** — la compuerta: `quality.yaml`, `quality.json` y exit code real.
5. **Frente 5** — splits estratificados con semilla y sin fuga.
6. **Frente 6** — `dvc init`, pipeline por etapas y remotes DEV/PROD.
