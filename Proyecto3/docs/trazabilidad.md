# Trazabilidad de la entrega (F11 T30)

La cadena completa, del dataset a una predicción en el portal. Cada fila dice
**dónde se comprueba** el valor, para que cualquiera lo verifique sin creernos.
Todos los hashes son SHA-256 salvo que diga md5 (DVC).

## La cadena

| # | Eslabón | Identificador | Hash / versión | Dónde se comprueba |
|---|---|---|---|---|
| 1 | Release del dataset (P2) | `0.1.3`, compuerta `pass` | huella P2 `2200274dc6bbe6d0bc516e0136ae68651c0040bc6cab64a871794924fa39aa84`; archivo `787742988af1df41d9a58573b81b5c9b4fe7ab24a647b25f2e71d3eb323838b5` | `Proyecto2/reports/versions.json`; `GET /api/p3/releases/0.1.3` |
| 2 | Imágenes del release en DVC | `Proyecto2/data/raw.dvc` | md5 `ca56420c9992f8b75fdb10f2ece81704.dir` (2046 archivos) | remote `prod` = `s3://dataset-quality-dvc-cache-750702272375`; `dvc pull` |
| 3 | Archivo del release en S3 | `s3://dataset-quality-releases-750702272375/0.1.3/dataset.tar.zst` | `787742988af1…` (el de la fila 1) | `p3.data.releases.open_release_archive` verifica SHA-256, huella y `quality.json` |
| 4 | Clases | `cat`=0, `dog`=1, `person`=2 | fijadas en `219fed3` (25 sep), antes de la primera corrida (26 sep) | `Proyecto3/config/classes.yaml`; [clases.md](clases.md) |
| 5 | Recortes | 1459 recortes de 1101 originales | `crops.jsonl` `d3d61f35a3efb60e665ac16c95a18f1602df44f3df7c22b86e1c949fadbe1bed` | `scripts/generate_crops.py`; [verificacion_recortes.md](verificacion_recortes.md) |
| 6 | Manifiesto 70/20/10 | `m-0.1.3-s42-1`, seed 42 | `manifest.jsonl` `45600f297d13f51685e051e0cbc4962beb1f7c6a4e03247cbf61a345e6fa4305`; puntero DVC md5 `64eae7e52ddd9c73261680c860805494.dir` | tag `p3-manifiesto-congelado`; `p3.data.frozen`; `POST /api/p3/manifests`; [manifiesto.md](manifiesto.md) |
| 7 | Partición | train 1022 / val 292 / test 145 | 0 en las 9 intersecciones (recorte, original, grupo de casi duplicados) | `check_manifest`; [manifiesto.md](manifiesto.md#evidencia-de-aislamiento-m3) |
| 8 | Barrido en MLflow | experimento `p3-clasificador` (id 3), 12 corridas válidas sobre el manifiesto | snapshot `mlflow_snapshot.dvc` md5 `b1cc30661a913830d72c91d663a90df7.dir` | `dvc pull mlflow_snapshot.dvc` → MLflow en `:5000`; `GET /api/p3/runs` |
| 9 | Corrida seleccionada (r10) | run `9f9b62c202f0446a8a4b411a10321eff`, trabajo `c953c0beeba14b439f12faa3f27528a9` | código `250bedcf6e89b808b6670792da176219f7b4c4d4` (limpio); ResNet-18 ImageNet, adamw, lr 1e-4, batch 64, dropout 0.5, seed 42 | tags y parámetros del run en MLflow |
| 10 | Selección por validación | `val_accuracy` 0.99658, `val_loss` 0.02425, mejor época 6 | regla: máx `val_accuracy`, desempate mín `val_loss` | [selection.json](selection.json); `GET /api/p3/selection` |
| 11 | Checkpoint | `checkpoint/model.pt` del run | `e4acca429ebf73d0e5a60fb0dda383a6a5322dccb1decf04b4e40ab9db989172` | `selection.json` = artefacto de MLflow = `model.pt` en S3 |
| 12 | Evaluación única en test | 145 recortes, 142 aciertos: accuracy 0.9793, F1 macro 0.9744 (umbral 0.85: pasa) | baseline de clase mayoritaria (`person`) 0.5172; `predictions_test.csv` `575da62412e7d68e04c7a55ee3ec574e2813607a1a2e3c08c2e5ab51e8a6f492`; código `a7ec1dc` | `reports/evaluation/9f9b62c2…/metrics.json`; artefactos `evaluation/` del run; `GET /api/p3/evaluation`; [analisis_errores.md](analisis_errores.md) |
| 13 | Versión del modelo | **1.0.0** (activa) = r10 | `model.pt` `e4acca42…` (el de la fila 11) | `registry.json`; `GET /api/p3/models` |
| 14 | Objeto en S3 | `s3://dataset-quality-releases-750702272375/models/clasificador/1.0.0/model.pt` | `VersionId` `VtRww5se97lomVTcKJUv6d9mYSL7TXOf`; tarjeta `7LNRNnVo01WUgE.aDEHjCya.n7fnDWZg` | `aws s3api head-object`; [publicacion_s3.md](publicacion_s3.md) |
| 15 | Versión alternativa | 0.9.0 = r08 `5ebc2c9f94fa491e9e9adc7b7c8184ac`, sin evaluación en test | `model.pt` `ab4d1f44…`, `VersionId` `ElFQBtWzSAoR0zJAk7av.PR00H_v2OeI` | para demostrar el cambio de versión en Models |
| 16 | Inferencia desde el portal | las 145 imágenes de test por `POST /api/p3/inference` | 145/145 con la misma clase y probabilidades (±1e-4) que `predictions_test.csv` | `scripts/verify_inference.py`; [F4 T24](fases/F4-modelo-entrenador.md) |
| 17 | Envío a la cola de anotación (P1) | inferencia `1294c24f…` → `image_id` 9 en P1, `pending` | archivo con el mismo SHA-256 que la foto enviada (`0bbe9272…`) | `POST /api/p3/inference/{id}/send-to-annotation`; `GET :3000/api/images/9` |

## Cómo verificar la cadena en cinco comandos

```bash
cd Proyecto3
dvc pull data/manifests/m-0.1.3-s42-1.dvc mlflow_snapshot.dvc
sha256sum data/manifests/m-0.1.3-s42-1/manifest.jsonl   # 45600f29… (fila 6)
python -c "import json; print(json.load(open('docs/selection.json'))['checkpoint_sha256'])"   # e4acca42… (fila 11)
aws s3api head-object --bucket dataset-quality-releases-750702272375 --key models/clasificador/1.0.0/model.pt --profile <perfil>   # VersionId VtRww5se… (fila 14)
```

Después, con el stack arriba (`python scripts/up.py`), `GET /api/p3/models` debe
mostrar 1.0.0 activa con ese `VersionId` y SHA-256, y una predicción en Inference
debe salir de ese mismo archivo.

## Pendiente del ensayo del 30 de septiembre

- Fila 17: repetir el envío a la cola con el stack de la entrega y anotar el id completo de la inferencia.
- Registrar el commit final con el tag `p3-entrega` y su corrida de CI en verde.
