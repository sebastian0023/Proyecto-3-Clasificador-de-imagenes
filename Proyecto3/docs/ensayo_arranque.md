# Ensayo de arranque desde clon limpio (F10 T28 · compuerta M1/M4)

Objetivo: que el evaluador levante todo siguiendo el [README](../../README.md)
al pie de la letra, recorra las 5 páginas con datos reales, recargue durante un
trabajo, cambie la versión del modelo, pruebe un archivo inválido, y cargue el
checkpoint publicado en un proceso limpio para inferir (M4).

**Estado:** ensayo **parcial** hecho el 27 sep 2026 (lo que no depende del stack
completo). El ensayo **completo** es del miércoles 30, cuando F4–F7 estén en
`main` (entrenador/MLflow, selección, evaluación, publicación en S3): sin ellas
no hay modelo real que cargar ni predicción real que hacer.

## Checklist

| Paso del README | Estado | Evidencia / nota |
|---|---|---|
| §Pruebas de P3: `venv` + `pip install -r requirements.lock.txt` + `-e .` | ✅ verificado | Instalación limpia OK en Python 3.12. |
| §Pruebas de P3: `ruff check .` + `ruff format --check .` | ✅ verificado | Sin hallazgos; 52 archivos formateados. |
| §Pruebas de P3: `pytest` | ✅ verificado | **144 passed, 2 skipped** (los 2 skips: el flujo E2E completo y un caso ya marcado). |
| Portal `Proyecto2/web`: `npm ci` + `npm run test:unit` + `npm run build` | ✅ verificado | 31/31 pruebas de componente; build/typecheck limpios. |
| `python scripts/up.py` levanta app + MariaDB + MinIO + MLflow desde clon limpio | ⏳ pendiente | Necesita Docker; se valida en el ensayo del 30 (el job `smoke` de `ci.yml` ya lo prueba para P2). |
| Las 5 páginas (Training, Experiments, Evaluation, Models, Inference) con **datos reales** | ⏳ pendiente | Hoy corren contra el mock/contrato; datos reales cuando F4–F7 estén en `main`. |
| Recargar durante un trabajo corto conserva estado y logs | ⏳ pendiente | Mecanismo implementado y probado contra el mock (T19); recarga real contra el backend el 30. |
| Cambiar la versión del modelo (Models) | ⏳ pendiente | Página Models es F9. |
| Probar un archivo inválido (Inference) | ⏳ pendiente | Página Inference es F9. |
| M4: cargar el checkpoint publicado en un proceso limpio e inferir | ⏳ pendiente | Necesita F4 (modelo) y F7 (S3). |

## Observaciones sobre el README (a confirmar/corregir en el ensayo del 30)

1. **Build del frontend en el arranque.** El README levanta con `up.py` pero no
   dice si el build de Vite (`Proyecto2/web` → `src/dataset_quality/static/`) se
   hace dentro de la imagen o hay que correrlo antes. Si el contenedor no lo
   construye, las 5 páginas saldrían vacías desde un clon limpio. Verificar en el
   ensayo y, si falta, documentar el `npm ci && npm run build` previo (como hace
   el job `smoke` de la CI).
2. **Pruebas del portal.** La sección §Pruebas de P3 solo cubre Python; conviene
   añadir las pruebas de componente del portal (`Proyecto2/web`: `npm run
   test:unit`), que ya bloquean cada PR en `ci.yml`.
3. **Perfil de AWS para el dataset.** El `dvc pull` exige un perfil autorizado en
   `~/.aws`; el evaluador sin credenciales solo podrá usar el fixture. Dejar
   claro qué se puede hacer sin el dataset real.

Cuando F4–F7 estén en `main`, se ejecuta el ensayo completo en una máquina/carpeta
limpia, se corrigen los pasos que fallen **en el momento**, y se marcan aquí las
casillas ⏳ con su evidencia (salida de comando, capturas de las 5 páginas).
