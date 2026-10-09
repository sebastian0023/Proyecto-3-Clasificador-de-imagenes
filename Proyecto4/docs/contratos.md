# Contratos — Proyecto 4

> **Borrador.** Los campos salen de la tarjeta F1 y de las reglas de F3 y F4. Los nombres de campo y el formato son una **propuesta**: Bryan y Emilio los acuerdan en F1 y, cuando estén de acuerdo, cambian el estado a *congelado*. Después, cualquier cambio de forma va explícito en el PR y se avisa al equipo.

Estado: **borrador**

## Evento de captura

Lo produce el dispositivo (F3), lo recibe y persiste AWS (F4) y lo muestra Capturas Edge (F5).

| Campo | Tipo | Regla |
|---|---|---|
| `capture_id` | texto | ID único de la captura. Es la clave de idempotencia: el mismo ID enviado dos veces deja un solo registro. |
| `captured_at` | fecha y hora | Con zona horaria (por ejemplo ISO 8601 con offset). Se rechaza o se señala si no la trae. |
| `predicted_class` | texto | Una de las clases declaradas del modelo del P3, en el orden del paquete. |
| `confidence` | número | Entre 0 y 1, ambos incluidos. Fuera de rango se rechaza o se señala. |
| `device_id` | texto | Identidad configurable del dispositivo. |
| `model_version` | texto | Versión del artefacto optimizado cargado. Sin ella se rechaza o se señala. |
| `model_sha256` | texto | SHA-256 de la variante cargada, el mismo que muestra el programa al arrancar. |
| `image_ref` | texto | Referencia a la fotografía local. |
| `region` | objeto, opcional | Región clasificada si hay recorte (x, y, ancho, alto en píxeles de la fotografía). |

Campos que agrega la recepción en AWS (F4), no los envía el dispositivo:

| Campo | Tipo | Regla |
|---|---|---|
| `received_at` | fecha y hora | Cuándo recibió AWS el evento. |
| `image_key` | texto | Clave del objeto con la fotografía en el servicio de almacenamiento. |

Ejemplo (propuesta):

```json
{
  "capture_id": "edge01-20261009T153012-0007",
  "captured_at": "2026-10-09T15:30:12-06:00",
  "predicted_class": "<clase>",
  "confidence": 0.93,
  "device_id": "edge01",
  "model_version": "<version-del-artefacto-optimizado>",
  "model_sha256": "<sha256>",
  "image_ref": "capturas/edge01-20261009T153012-0007.jpg",
  "region": null
}
```

## Reglas de recepción (F4)

1. La fotografía y los metadatos llegan juntos y se guardan: imagen en almacenamiento, registro con `received_at` e `image_key`.
2. Un evento sin zona horaria, con confianza fuera de 0 a 1 o sin versión del artefacto se rechaza o se señala; nunca se persiste en silencio como válido.
3. Un reintento con el mismo `capture_id` no crea un duplicado.
4. El listado para el portal sale ordenado de más reciente a más antigua.
5. Hay exportación de eventos en CSV o JSON con los campos del evento.

## Comportamiento del dispositivo ante fallos (F3, F6, F9)

1. El registro local (imagen y evento) se conserva aunque el envío falle.
2. El error se muestra en el dispositivo y el reintento manual reutiliza el mismo `capture_id`.
3. Reiniciar el programa no borra el historial local.

## Modelo y paquete de entrada

Lo define el paquete del modelo del Proyecto 3 y lo reutilizan F2, F3 y F7; no se redefine aquí.

- Orden de clases, tamaño de entrada, canales, normalización y orden RGB/BGR: los del modelo original (`Proyecto3/docs/modelo.md`).
- Si la variante cuantiza la entrada, la cuantización queda documentada en la ficha del artefacto (F2) y el dispositivo la aplica igual (F3).

## Registros que se comparan entre fases

| Registro | Lo produce | Lo consume | Contenido mínimo |
|---|---|---|---|
| Registro de conversión | F2 | F3, F7, F10 | Archivo de entrada y de salida con SHA-256, técnica, configuración, versiones. |
| Predicciones por muestra | F7 | F3 (entradas conocidas), F10 | Identificador, clase real, clase del original, clase del optimizado. |
| Tiempos por repetición | F8 | F10 | Variante, número de repetición, milisegundos de preprocesamiento más inferencia; calentamiento identificado y excluido. |
| Exportación de eventos | F4, F9 | F10, F11 | Campos del evento de captura. |
