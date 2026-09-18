# Reproducibilidad del pipeline DVC

Generado por `python scripts/evidencia_dvc.py` el 2026-09-18T18:57:51+00:00.

## Veredicto

**El pipeline es reproducible.** La segunda corrida de `dvc repro` no
ejecuto ninguna etapa y los hashes de `dvc.lock` no se movieron.

| Comprobacion | Resultado |
| --- | --- |
| Etapas ejecutadas en la 1a corrida | ninguna |
| Etapas ejecutadas en la 2a corrida | ninguna |
| Hashes de `dvc.lock` estables | si |
| Cache local contra remote `dev` | en sincronia |
| Cache local contra remote `prod` | en sincronia |

## Hashes de salida registrados en `dvc.lock`

Son los mismos en DEV y en PROD porque el hash lo determina el CONTENIDO,
no el destino: `dvc status -r dev` y `-r prod` contrastan este mismo cache
local contra cada remote.

| Etapa | Salida | md5 |
| --- | --- | --- |
| analyze | `reports/exploration.json` | `61f80004ca24fd9dfcfd11c04fac1c97` |
| analyze | `reports/stats.json` | `d5adc82578f9c784eef32285e146bbd3` |
| gate | `reports/quality.json` | `bb1dd8230b2b80fcd35171befdda3aef` |
| split | `reports/splits.json` | `f124b71ee47cc553f5d295ad38aeafa8` |
| release | `reports/versions.json` | `29f0f61b40bdf750215ba764c99720c9` |

## Salida cruda de cada comando

### Primera corrida

`$ C:\Users\angel\OneDrive\Documentos\semestre 9 intercambio\mlops\proyecto 2\ruta-al-dataset-v1\Proyecto2\.venv\Scripts\python.exe -m dvc repro` (exit 0)

```
Stage 'analyze' didn't change, skipping
Stage 'gate' didn't change, skipping
Stage 'split' didn't change, skipping
Stage 'release' didn't change, skipping
Data and pipelines are up to date.
```

### Segunda corrida

`$ C:\Users\angel\OneDrive\Documentos\semestre 9 intercambio\mlops\proyecto 2\ruta-al-dataset-v1\Proyecto2\.venv\Scripts\python.exe -m dvc repro` (exit 0)

```
Stage 'analyze' didn't change, skipping
Stage 'gate' didn't change, skipping
Stage 'split' didn't change, skipping
Stage 'release' didn't change, skipping
Data and pipelines are up to date.
```

### Estado del grafo

`$ C:\Users\angel\OneDrive\Documentos\semestre 9 intercambio\mlops\proyecto 2\ruta-al-dataset-v1\Proyecto2\.venv\Scripts\python.exe -m dvc status` (exit 0)

```
Data and pipelines are up to date.
```

### Estado contra el remote dev

`$ C:\Users\angel\OneDrive\Documentos\semestre 9 intercambio\mlops\proyecto 2\ruta-al-dataset-v1\Proyecto2\.venv\Scripts\python.exe -m dvc status -r dev` (exit 0)

```
Cache and remote 'dev' are in sync.
```

### Estado contra el remote prod

`$ C:\Users\angel\OneDrive\Documentos\semestre 9 intercambio\mlops\proyecto 2\ruta-al-dataset-v1\Proyecto2\.venv\Scripts\python.exe -m dvc status -r prod` (exit 0)

```
Cache and remote 'prod' are in sync.
```
