# Clases del clasificador — Proyecto 3 (F2 T06)

Clases fijadas **antes de cualquier experimento**, con conteos recalculados sobre el release aprobado. La fecha del commit que agrega [`config/classes.yaml`](../config/classes.yaml) es la evidencia de que se decidieron antes de ver resultados (criterios 1.2 y 3.1; regla 9 de `AGENTS.md`).

## Decisión

**3 clases: `cat`, `dog` y `person`.** Se excluyen `car` y `bicycle`.

| `class_index` | Clase | `category_id` | Originales con caja válida | Cajas válidas | Decisión |
|---:|---|---:|---:|---:|---|
| 0 | cat | 4 | **312** | 329 | Incluida |
| 1 | dog | 3 | **348** | 379 | Incluida |
| 2 | person | 2 | **441** | 751 | Incluida |
| — | car | 1 | 247 | 320 | Excluida: 247 < 300 |
| — | bicycle | 5 | 239 | 340 | Excluida: 239 < 300 |

`class_index` es el orden alfabético del nombre, igual que [contratos.md §1](contratos.md#1-mapa-de-clases).

## Regla (predeclarada, sin resultados de modelo)

1. Se valida cada caja del release con `p3.data.crops.validate_annotations`: se descartan cajas degeneradas, fuera de la imagen o de imágenes faltantes.
2. Por categoría se cuentan **imágenes originales distintas** con al menos una caja válida (`p3.data.classes.originals_per_category`). Se cuentan originales, no recortes: una imagen con tres personas cuenta una vez.
3. Entra toda categoría con **≥ 300 originales** (`select_classes`); se exige un mínimo de 2 clases.

La exclusión de `car` y `bicycle` depende solo de ese umbral. No se agregan ni se quitan clases después de ver validación o prueba.

**Sin filtro por tamaño de caja.** Las cajas diminutas (231 de 2120, 10.9 %: menos del 2 % del área de su imagen o menos de 1024 px², según `Proyecto2/reports/stats.json`) **se conservan**: el contrato solo define los cuatro motivos de exclusión de [contratos.md §2](contratos.md#2-manifiesto-de-recortes-702010--contrato-f2-f3). Cambiar esta regla después de ver el test contaría como resultado inflado.

## Procedencia verificada

Salida de `scripts/count_classes.py --release 0.1.3` (25 sep 2026, perfil de solo lectura):

| Comprobación | Resultado |
|---|---|
| Release | `0.1.3`, `quality_status: pass` |
| `dataset_fingerprint` | `2200274dc6bbe6d0bc516e0136ae68651c0040bc6cab64a871794924fa39aa84` |
| `quality_report_fingerprint` | `4d6e64aa13c6f66b15801811c4bb84ebc265b07f538ae27982f79628b170631a` |
| Archivo | `s3://dataset-quality-releases-750702272375/0.1.3/dataset.tar.zst`, `VersionId riojb0ulsh1fzPYrMiAicAGps.5f1JBI` |
| SHA-256 del archivo descargado | coincide con `archive_sha256` (`787742988af1…`) |
| Huella de P2 del COCO del archivo | coincide con `dataset_fingerprint` |
| Huella del COCO de DVC (`Proyecto2/data/raw`, `dvc pull -r prod`) | coincide: las imágenes son las del release |
| Imágenes | 2045 en el COCO, 2045 legibles |
| Anotaciones | 2120; 2119 válidas; 1 excluida (`bbox_out_of_bounds`, de `bicycle`) |

## Riesgo registrado

`person` aporta 751 de las 1459 cajas válidas de las tres clases (≈ 51 %). El baseline de clase mayoritaria ronda ese valor, así que la evaluación (F6) reporta F1 macro, recall por clase y baseline junto con el accuracy.

## Reproducir

```bash
cd Proyecto2
.venv/Scripts/dvc pull -r prod data/raw.dvc
PYTHONPATH=../Proyecto3/src .venv/Scripts/python ../Proyecto3/scripts/count_classes.py --release 0.1.3 --profile <perfil-aws>
```

Con `--write` regenera `config/classes.yaml`; `tests/test_classes_config.py` falla si el archivo deja de coincidir con esta decisión.
