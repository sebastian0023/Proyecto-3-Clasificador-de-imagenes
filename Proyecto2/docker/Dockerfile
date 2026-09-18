# syntax=docker/dockerfile:1

# --- Etapa 1: compilar la app web (Frente 7) --------------------------------
FROM node:22-slim AS web

WORKDIR /web
# Las dependencias cambian mucho menos que el codigo: capa propia y cacheada.
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
# Se compila a /web/dist en vez del outDir del vite.config, porque dentro de
# esta etapa no existe el arbol `src/` del repositorio.
RUN npx vite build --outDir /web/dist --emptyOutDir


# --- Etapa 2: la aplicacion --------------------------------------------------
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # El paquete se instala editable para recarga en desarrollo; conservar la
    # ruta explicita hace que uvicorn encuentre tanto la app como el sidecar.
    PYTHONPATH=/app/src

WORKDIR /app

# Las dependencias cambian mucho menos que el codigo: capa propia y cacheada.
COPY pyproject.toml README.md quality.yaml ./
COPY src ./src
RUN pip install --no-cache-dir -e ".[dev]"

# El build de la web va FUERA de `src/`, y `DQ_STATIC_DIR` le dice a `main.py`
# donde buscarlo. Dentro de `src/` no puede vivir: compose monta ahi el codigo
# del host para recargar uvicorn en caliente, y ese montaje taparia el build
# que esta imagen acaba de compilar. Como el build esta en `.gitignore`, el
# host de quien clona el repositorio no tiene nada que poner en su lugar.
COPY --from=web /web/dist /opt/dq/static
ENV DQ_STATIC_DIR=/opt/dq/static

# Usuario sin privilegios: el contenedor nunca corre como root.
RUN useradd --create-home --uid 10001 appuser && chown -R appuser:appuser /app /opt/dq
USER appuser

EXPOSE 8000

CMD ["uvicorn", "dataset_quality.main:app", "--host", "0.0.0.0", "--port", "8000"]
