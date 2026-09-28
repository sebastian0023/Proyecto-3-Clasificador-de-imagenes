# Pruebas de mutación — Proyecto 3 (F10 T26)

Las mutaciones prueban que la suite **detecta defectos**, no solo que calcula
sobre datos sanos (criterios 7.1 y 7.2). Cada mutación es un cambio manual y
temporal en el código de producción; se corre `pytest`, se confirma que la suite
**falla**, y se **revierte** de inmediato con `git checkout --`. Nunca se commitea
el código mutado: la evidencia es esta tabla.

Todas se ejecutan en `Proyecto3/` con el entorno del lockfile
(`pip install -r requirements.lock.txt`).

## M-A · Un grupo de casi duplicados se parte entre train y test

**Defecto inyectado.** En `src/p3/data/split.py`, `dup_group_ids` deja de honrar
los grupos de casi duplicados (pHash de P2) y devuelve un grupo propio por imagen:

```diff
-    return {image_id: assigned.get(image_id, f"g{image_id}") for image_id in sorted(image_ids)}
+    return {image_id: f"g{image_id}" for image_id in sorted(image_ids)}
```

Con esto dos imágenes casi idénticas pueden caer en particiones distintas: la
fuga que el criterio 3.3/M3 prohíbe.

**La suite lo detecta** (`pytest tests/test_split.py`):

```
FAILED tests/test_split.py::test_dup_group_id_es_g_mas_el_menor_image_id
FAILED tests/test_split.py::test_los_casi_duplicados_viajan_juntos
FAILED tests/test_split.py::test_muchos_pares_de_casi_duplicados_nunca_se_separan
```

Revertido con `git checkout -- src/p3/data/split.py` → 24/24 en verde.

## M-B · La red de seguridad `check_manifest` deja de ver la fuga

**Defecto inyectado.** En `check_manifest`, la comprobación de aislamiento solo
mira `crop_id` y ya no `source_image_id` ni `dup_group_id`:

```diff
-    for field in ("crop_id", "source_image_id", "dup_group_id"):
+    for field in ("crop_id",):
```

Un manifiesto con el mismo original (distinto `crop_id`) en dos particiones ya no
se reporta: el verificador que correría el evaluador quedaría ciego a la fuga.

**La suite lo detecta** (`pytest tests/test_split.py`):

```
FAILED tests/test_split.py::test_check_manifest_detecta_un_original_en_dos_particiones
```

Revertido con `git checkout -- src/p3/data/split.py` → suite en verde.

## Pendiente (con F6 en `main`)

El criterio T26 también admite "alterar una predicción en la matriz de confusión".
Esa mutación vive sobre la evaluación en test (F6), que aún no está en `main`; se
añade aquí cuando la fase aterrice, junto a la E2E completa (ver
[`tests/test_e2e.py`](../tests/test_e2e.py)).
