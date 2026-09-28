# Tarjeta del modelo — clasificador `{version}`

Generada automáticamente a partir de `selection.json`, la evaluación final en test (F6) y la corrida de MLflow. Describe exactamente el `model.pt` de este paquete.

## Propósito

Clasificar **un objeto por imagen** (un recorte de una caja COCO) en una de tres clases: {classes}. Se usa desde la página Inference del portal del Proyecto 3. No es un detector: espera un recorte centrado en un solo objeto.

## Modelo

| Campo | Valor |
|---|---|
| Versión del modelo | `{version}` (semántica; no es la versión del dataset) |
| Arquitectura | `{arch_name}`, cabeza `hidden_layers={arch_hidden}`, dropout {arch_dropout}, {arch_classes} salidas |
| Pesos iniciales | {pretrained} (preentrenados en ImageNet); **todas las capas se reentrenaron** (fine-tuning completo) |
| Corrida de MLflow | `{run_id}` (experimento `p3-clasificador`) |
| Mejor época (early stopping) | {best_epoch}; `val_accuracy` {val_accuracy} |
| Commit del código de entrenamiento | `{code_commit}` |
| SHA-256 de `model.pt` | `{checkpoint_sha}` |

Configuración de entrenamiento: `{training}`.

## Datos

| Campo | Valor |
|---|---|
| Release de origen (Proyecto 2) | `{release_id}`, huella `{release_hash}`, compuerta de calidad aprobada |
| Imágenes (DVC) | `Proyecto2/data/raw.dvc`, md5 `{dvc_md5}` |
| Manifiesto | `{manifest_id}`, hash `{manifest_hash}`; split **70/20/10** agrupado por original y por casi duplicados, sin fuga |
| Recortes | `crops.jsonl` con SHA-256 `{crops_sha}` |
| Clases excluidas | las que no llegan a 300 originales en el release (`car`, `bicycle`); ver `docs/clases.md` |

## Desempeño en test

Evaluación **única** sobre el test congelado ({test_size} recortes), después de la selección por validación (`evaluated_at` {evaluated_at}).

| Métrica | Valor |
|---|---|
| Accuracy top-1 | **{accuracy}** ({correct} / {test_size}) |
| F1 macro | {f1_macro} |
| Baseline de clase mayoritaria (`{baseline_class}`, mismo test) | {baseline_accuracy} |

| Clase | Precisión | Recall | F1 | Support |
|---|---:|---:|---:|---:|
{rows_class}

Matriz de confusión (filas = real, columnas = predicho):

| real \ pred | {labels} |
|---|{label_rules}
{rows_matrix}

{confused_text} Predicciones por muestra: `reports/evaluation/{run_id}/predictions_test.csv` y `GET /api/p3/evaluation/predictions`.

## Preprocesamiento

El mismo en validación, test e inferencia: la imagen en RGB con la rotación EXIF aplicada, redimensionada a **{size}x{size}** estirándola (`{resize}`), sin recortar bordes, y normalizada con media `{mean}` y desviación `{std}` (ImageNet).

## Limitaciones

- Solo distingue tres clases; cualquier otro objeto se asignará a la más parecida.
- Clasifica recortes, no imágenes completas: si dos objetos se enciman, el recorte de uno incluye al otro y domina el que ocupa más espacio (en test, una persona cargando un perro se predijo como `dog`).
- Los gatos oscuros, a contraluz o sin rostro visible son los casos que más confunde con `dog`.
- El 10.9 % de las cajas del release son muy pequeñas (menos del 2 % del área de su imagen); se conservaron en entrenamiento, pero su calidad visual es baja.
- El test tiene {test_size} recortes: una diferencia de pocos puntos entre versiones puede no ser significativa.

## Cómo cargarlo

```python
from pathlib import Path
import torch
from PIL import Image, ImageOps
from p3.data.transforms import build_eval_transform
from p3.model.build import load_checkpoint

model, meta = load_checkpoint(Path("model.pt"))  # modo eval, pesos y clases
transform = build_eval_transform(meta["preprocessing"]["image_size"])
with Image.open("recorte.png") as handle:
    image = ImageOps.exif_transpose(handle).convert("RGB")
with torch.no_grad():
    probs = torch.softmax(model(transform(image).unsqueeze(0)), dim=1)[0]
print(dict(zip(meta["class_names"], probs.tolist())))
```

Dependencias exactas en `requirements.lock.txt` (Python 3.12, `torch` y `torchvision` fijados).
