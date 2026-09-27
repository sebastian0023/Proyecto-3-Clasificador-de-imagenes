# Imagen del worker de entrenamiento de Proyecto 3.
# Se construye desde `Proyecto2/docker-compose.yml` (servicio `p3-worker`) con
# `Proyecto3/` como contexto. Python 3.12 fijado igual que en Proyecto2.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    TORCH_HOME=/opt/torch \
    CUBLAS_WORKSPACE_CONFIG=:4096:8

WORKDIR /app

# Dependencias desde el lockfile, antes del codigo: cambiar un .py no reinstala.
COPY requirements.lock.txt ./
RUN pip install --no-cache-dir -r requirements.lock.txt

# Pesos de ImageNet de ResNet-18 dentro de la imagen: las corridas no dependen
# de la red y todas parten del mismo archivo (torchvision verifica su hash).
RUN python -c "from torchvision.models import ResNet18_Weights; ResNet18_Weights.IMAGENET1K_V1.get_state_dict(progress=False)" \
    && chmod -R a+rX /opt/torch

COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir --no-deps -e .

RUN useradd --create-home --uid 10001 appuser && chown -R appuser:appuser /app
USER appuser

CMD ["python", "-m", "p3.worker.runner"]
