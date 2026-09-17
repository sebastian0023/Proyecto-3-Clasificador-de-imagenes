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
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Las dependencias cambian mucho menos que el codigo: capa propia y cacheada.
COPY pyproject.toml README.md quality.yaml ./
COPY src ./src
RUN pip install --no-cache-dir -e ".[dev]"

# El build de la web va donde `main.py` lo busca. Compose monta `./src` en
# vivo, asi que en desarrollo se ve el build del host; en una imagen sin
# montaje, este.
COPY --from=web /web/dist ./src/dataset_quality/static

# Usuario sin privilegios: el contenedor nunca corre como root.
RUN useradd --create-home --uid 10001 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "dataset_quality.main:app", "--host", "0.0.0.0", "--port", "8000"]
