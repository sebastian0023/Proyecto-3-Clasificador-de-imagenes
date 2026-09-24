# F4 — Modelo, entrenador y servicio de inferencia

| Campo | Valor |
|---|---|
| Responsable | Edith (Líder de ML y MLOps) |
| Revisor de PRs | Andrés |
| Fechas | 25 sep → 29 sep de 2026 |
| Rama | `feat/fase-4-modelo-entrenador` |
| Puntos de rúbrica | 18 (2.1–2.4, M4 (compuerta)) |
| Depende de | F1 |
| Bloquea a | F5, F9 |
| Control | Control 2 |

**Nota de calendario:** El viernes 25 se mide una corrida corta y se calendariza el barrido. Entrenador con early stopping listo el lunes 28 en la mañana; el servicio de inferencia se hace el martes mientras corre el barrido y se verifica con el objeto real de S3 el miércoles.

> Antes de empezar lee `AGENTS.md` (contexto y reglas) y `docs/p3/contratos.md`. Trabaja los bloques en orden; cada bloque es al menos un PR.

## Bloque T09 — Dataset, DataLoader y transforms (aumentación solo en train)

**Objetivo:** Leer el manifiesto y construir DataLoaders con aumentación exclusiva de train y un preprocesamiento determinista compartido por val, test e inferencia.

**Criterios de rúbrica:** 2.3, M3

**Pasos**

1. Pruebas primero: val/test/inferencia usan exactamente la misma función de preprocesamiento; aplicar dos veces el transform de val a la misma imagen da el mismo tensor; el dataset de train nunca incluye ids de val/test.
2. Implementa src/p3/data/transforms.py con build_train_transform(cfg) y build_eval_transform(cfg) (resize a image_size, normalización ImageNet).
3. Implementa CropDataset que lee el manifiesto (esquema de docs/p3/contratos.md) filtrando por split.
4. Implementa DataLoaders con generator y worker_init_fn sembrados para orden reproducible.

**Aceptación** (marca al cumplir, con enlace a la evidencia)

- [ ] Mismo seed -> mismo orden de muestras (prueba)
- [ ] Transform aleatorio solo en train (prueba)

**Entregables:** `src/p3/data/transforms.py`; `src/p3/data/dataset.py`; Pruebas

## Bloque T10 — Modelo CNN configurable (ResNet18 + cabeza propia)

**Objetivo:** Construir el clasificador con cabeza adaptada a las clases y parámetros hidden_layers y dropout.

**Criterios de rúbrica:** 2.1

**Pasos**

1. Pruebas primero: la salida tiene tamaño = número de clases de classes.yaml; tras 3 pasos de optimizador los pesos de la cabeza cambian; el modelo se guarda y recarga con mapa de clases idéntico.
2. Implementa build_model(cfg, num_classes): backbone torchvision ResNet18 con pesos ImageNet (documenta origen y licencia) y cabeza MLP con hidden_layers y dropout configurables; documenta qué capas son entrenables.
3. Documenta en docs/p3/modelo.md la arquitectura, el origen de pesos iniciales y la justificación.

**Aceptación** (marca al cumplir, con enlace a la evidencia)

- [ ] Prueba de cambio de pesos pasa
- [ ] docs/p3/modelo.md declara origen de pesos

**Entregables:** `src/p3/model/build.py`; `docs/p3/modelo.md`

## Bloque T11 — Loop por minibatches, config validada y semillas

**Objetivo:** Entrenador por minibatches con configuración validada antes de crear el trabajo y todas las semillas registradas.

**Criterios de rúbrica:** 2.2, 2.3

**Pasos**

1. Pruebas primero: un valor inválido (batch_size=0, lr negativo, optimizador inexistente, dropout>=1) lanza error de validación con mensaje útil y NO crea trabajo; cada parámetro de la config cambia el comportamiento real (no se ignora).
2. Implementa TrainingConfig con Pydantic según contratos.md.
3. Implementa el loop: por época, por batch -> forward, loss, backward, optimizer.step(); calcula loss y accuracy de train y val por época.
4. Siembra random, numpy, torch (y cuda), DataLoader; registra versiones de librerías y torch.use_deterministic_algorithms donde sea posible, documentando lo no determinista.
5. Conecta el entrenador al worker de T02 para que un trabajo reporte progreso por época.

**Aceptación** (marca al cumplir, con enlace a la evidencia)

- [ ] Config inválida rechazada por API con 422
- [ ] Corrida corta con mismo seed reproduce orden de muestras

**Entregables:** `src/p3/train/config.py`; `src/p3/train/trainer.py`; Pruebas

## Bloque T32 — Medir una corrida corta y calendarizar el barrido

**Objetivo:** Saber con datos reales si las ≥10 corridas caben en el tiempo disponible antes de lanzarlas el lunes 28.

**Criterios de rúbrica:** 3.1 (riesgo: diez corridas sin presupuesto)

**Pasos**

1. Con el manifiesto provisional de Diego (o el fixture escalado si aún no existe), ejecuta una corrida corta por el worker: 2 épocas con image_size 128 y 224.
2. Mide segundos por época y memoria usada; estima la duración de cada combinación de config/p3/sweep.yaml con su max_epochs y el efecto esperado del early stopping.
3. Si el total estimado supera la ventana de la noche del lunes 28 al martes 29 a mediodía, ajusta: reduce image_size o max_epochs, paraleliza corridas o adelanta parte del barrido al fin de semana, sin romper la variación de los 7 parámetros.
4. Actualiza la decisión 7 (presupuesto de cómputo) en docs/p3/decisiones.md con la medición real y el calendario de corridas.

**Aceptación** (marca al cumplir, con enlace a la evidencia)

- [ ] Tiempo por época medido para al menos 2 tamaños de imagen
- [ ] Calendario del barrido documentado y dentro de la ventana

**Entregables:** `docs/p3/decisiones.md (decisión 7)`; `config/p3/sweep.yaml ajustado si hace falta`

## Bloque T12 — Early stopping con restauración y registro completo en MLflow

**Objetivo:** Detener cuando la métrica de validación deja de mejorar, restaurar la mejor época y registrar todo en MLflow.

**Criterios de rúbrica:** 2.4, 3.2

**Pasos**

1. Pruebas primero: con una secuencia simulada de val_accuracy [0.5,0.6,0.7,0.65,0.64,0.63] y patience=3 se detiene en la época 6 y el checkpoint final es el de la época 3.
2. Implementa EarlyStopping(monitor, patience, min_delta, mode) que guarda el state_dict de la mejor época y lo restaura al terminar.
3. Registra por corrida en MLflow: parámetros efectivos, semilla, commit git, release DVC, hash del manifiesto, lista de clases, métricas por época (train/val loss y accuracy), época de parada, mejor época, curvas PNG y checkpoint como artefacto.
4. Rechaza iniciar si el manifiesto no está congelado o su hash no coincide con el esperado.

**Aceptación** (marca al cumplir, con enlace a la evidencia)

- [ ] Prueba de secuencia controlada pasa
- [ ] Un run en MLflow muestra todos los campos listados vía API (mlflow.search_runs)

**Entregables:** `src/p3/train/early_stopping.py`; Integración MLflow

## Bloque T24 — Servicio de inferencia (backend)

**Objetivo:** Endpoint que infiere con los pesos reales de la versión activa, con el mismo preprocesamiento de evaluación.

**Criterios de rúbrica:** 6.5, M4

**Pasos**

1. Pruebas primero: rechaza tipos no imagen y archivos > límite (p. ej. 10 MB) con 400/413; las probabilidades suman 1±1e-4; cambiar la versión activa cambia el modelo cargado (hash distinto).
2. Implementa POST /api/p3/inference: acepta imagen completa + bbox opcional para recortar, aplica build_eval_transform, devuelve clase, probabilidades por clase, versión de modelo y id de inferencia persistido.
3. Implementa POST /api/p3/inference/{id}/send-to-annotation que crea un elemento real en la cola de anotación existente del P1.
4. Carga SIEMPRE el paquete de la versión activa publicado en S3: descárgalo, verifica su SHA-256 contra el registro y cachéalo en memoria por versión. Nunca uses un checkpoint local del entrenamiento. Hasta que F7 publique (miércoles 30), pruébalo contra MinIO o un bucket de prueba; el miércoles verifica con el objeto real de S3.

**Aceptación** (marca al cumplir, con enlace a la evidencia)

- [ ] Una predicción sobre una imagen de test coincide con predictions_test.csv
- [ ] El modelo usado se descargó de S3 y su SHA-256 coincide con el registro
- [ ] El elemento enviado aparece en la cola de anotación

**Entregables:** `src/p3/inference/service.py`; Endpoints; Pruebas

## Definición de terminado

- [ ] Todas las casillas de aceptación marcadas con evidencia real
- [ ] PRs fusionados con review de Andrés
- [ ] CI en verde en `main`
- [ ] Commits red → green visibles en el historial

## Registro de avance

| Fecha | Quién | Bloque | Qué se hizo / PR | Pendiente |
|---|---|---|---|---|
