# Guion de la demo F6 — fallo reversible, reintento y trazabilidad

Rúbrica 4.3 (5 puntos) y M3: se provoca un envío fallido **de forma reversible**, se muestra el error, se reintenta **el mismo evento** (mismo `capture_id`) y queda **un solo registro** del ID con su imagen recuperable, visible en Capturas Edge.

| Quién | Dónde | Qué |
|---|---|---|
| **Bryan** | Raspberry Pi (`edge01`), desde la raíz del repositorio | Programa de la cámara, corte y restauración de la red |
| **Emilio** | Su laptop (PowerShell, `Proyecto4\`) | Traza en S3 y portal con `scripts/trazar_captura.py`; portal desplegado en el navegador |

Programa del dispositivo (ya en `main`, [`dispositivo/edge_camera.py`](../dispositivo/edge_camera.py)): captura y clasifica cada ~5 s **aunque no haya red**; guarda foto y evento (`capturas/events.jsonl`) **antes** de enviar; si el envío falla por red o por 5xx, la captura entra en `capturas/pendientes.json` (persistente, sobrevive a reinicios) y se reenvía **con el mismo `capture_id`** en cada ciclo; `201` = guardada, `200` = «ya estaba guardado».

## Ensayo ya realizado

- **12 oct (Bryan):** corte de red con ruta *blackhole*: 7 capturas fallaron (`Fallo de conexión … [Errno 22] Invalid argument`, entre 1 y 7 veces cada una), quedaron en la cola y se reenviaron con `201` al quitar el bloqueo. Evidencia en `main`: [`evidencia_f3/ejecucion_offline.txt`](../evidencia_f3/ejecucion_offline.txt), [`ping_offline.txt`](../evidencia_f3/ping_offline.txt) y [`eventos.txt`](../evidencia_f3/eventos.txt).
- **13 oct (Emilio):** traza de esos 7 IDs en las tres fuentes: un solo registro por ID, imagen con el mismo SHA-256 en la foto de la Pi, el evento, S3 (metadatos y descarga) y el portal; clase, confianza, versión y SHA del modelo iguales (F6, Registro de avance).

## Antes de empezar (5 min)

1. **Emilio:** la EC2 encendida y el portal responde (`401` sin credenciales = arriba):
   ```powershell
   aws ec2 describe-instances --profile p4-emilio --region us-east-1 --instance-ids i-0348c123c4c126267 --query "Reservations[0].Instances[0].State.Name" --output text
   curl.exe -s -o NUL -w "%{http_code}`n" https://174-129-84-80.sslip.io/
   ```
2. **Bryan:** token de producción en la variable de entorno (no en el código ni en pantalla) y cola vacía:
   ```bash
   read -rs -p "Token: " P4_DEVICE_TOKEN && export P4_DEVICE_TOKEN && echo
   cat Proyecto4/dispositivo/capturas/pendientes.json   # debe ser [] o no existir
   ```
3. **Emilio:** credenciales del portal en su consola, para la traza:
   ```powershell
   $u = Read-Host "Usuario del portal"; $p = Read-Host -AsSecureString "Contrasena del portal"; $env:P4_PORTAL_USUARIO = $u; $env:P4_PORTAL_PASSWORD = [Runtime.InteropServices.Marshal]::PtrToStringBSTR([Runtime.InteropServices.Marshal]::SecureStringToBSTR($p)); Remove-Variable p
   ```

## Opción principal: cortar la red de la Pi hacia el portal (la del ensayo)

| Paso | Quién | Comando / acción | Qué se ve |
|---|---|---|---|
| 1 | Bryan | `python Proyecto4/dispositivo/edge_camera.py --model Proyecto4/modelo/model_int8.onnx --version 1.0.0-int8.1` | Versión y SHA-256 del modelo; cada captura con `¡Envío exitoso (201) a AWS!` |
| 2 | Bryan (otra terminal) | `sudo ip route add blackhole 174.129.84.80` (el comando del ensayo, confirmado por Bryan) | `ping 174.129.84.80` → `connect: Invalid argument` |
| 3 | Bryan | Mostrar 1 o 2 objetos a la cámara | La Pi **sigue clasificando**; `Fallo de conexión (… Invalid argument). Se guardará en disco…` |
| 4 | Bryan | `cat Proyecto4/dispositivo/capturas/pendientes.json` | Los `capture_id` que fallaron. **Anotar uno** (el «ID de la demo») |
| 5 | Bryan | `sudo ip route del blackhole 174.129.84.80` | — |
| 6 | Bryan | Esperar el siguiente ciclo (~5 s) | `--- Intentando reenviar N capturas pendientes ---` y `¡Envío exitoso (201) a AWS!` para **el mismo ID**; `pendientes.json` vuelve a `[]` |
| 7 | Emilio | Traza (abajo) y portal | Un solo registro, imagen recuperable, datos iguales |

El corte solo afecta a la ruta de la Pi hacia `174.129.84.80`: la sesión SSH con la Pi, la EC2, el portal y AWS no se tocan. Se revierte con el paso 5 (o reiniciando la Pi: la ruta no es persistente).

**Variante sin `ip route`:** apagar el Wi-Fi (`sudo nmcli radio wifi off` / `on`). Solo si el programa corre en la consola local de la Pi (teclado y monitor): por SSH sobre Wi-Fi se pierde la sesión.

## Opción alternativa: destino inválido con `--url`

Útil si no se puede tocar la red. El programa toma la URL de `--url` o de `P4_API_URL`.

1. **Bryan:** arrancar con un **host** que no existe (el dominio `.invalid` nunca resuelve, RFC 2606):
   ```bash
   python Proyecto4/dispositivo/edge_camera.py --model Proyecto4/modelo/model_int8.onnx --version 1.0.0-int8.1 --url https://p4-destino-invalido.invalid/api/p4/captures
   ```
   Cada captura muestra `Fallo de conexión (… Name or service not known …)` y entra en `pendientes.json`.
2. **Bryan:** `Ctrl+C` y volver a arrancar **sin** `--url` (URL correcta). La cola persiste: en el primer ciclo reenvía los pendientes con su `capture_id` original → `201`.

⚠️ **No usar una ruta inválida en el host correcto** (por ejemplo `…/api/p4/capturas`): Caddy responde `401`, el programa lo trata como rechazo definitivo (cualquier 4xx sale de la cola) y esa captura **no se reintenta**. El fallo tiene que ser de red (host inexistente, corte) o un 5xx.

## Después del reintento: trazabilidad (Emilio)

1. **Rápida, en vivo (S3 + portal):** con el ID de la demo:
   ```powershell
   .\.venv\Scripts\python scripts\trazar_captura.py --capture-id <ID> --salida C:\MLOps_Project_Four\evidencia_f6\demo\traza_<ID>.txt
   ```
   Esperado: `1 registro(s) con este ID`, VersionId del registro, `SHA-256 de la imagen` igual en S3 (metadatos y descarga) y portal, y `Resultado: TODO COINCIDE`.
   En la Pi, Bryan muestra lo mismo del lado del dispositivo:
   ```bash
   grep '"<ID>"' Proyecto4/dispositivo/capturas/events.jsonl
   sha256sum Proyecto4/dispositivo/capturas/<ID>.jpg
   ```
   El `image_sha256` del evento y el `sha256sum` de la foto deben ser el valor de la fila `SHA-256 de la imagen`.
2. **Completa (tres fuentes):** Bryan copia `capturas/events.jsonl` y `capturas/<ID>.jpg` a la laptop (USB o `scp`) y Emilio agrega `--events <ruta>\events.jsonl --fotos-dir <carpeta>`.
3. **Portal:** `https://174-129-84-80.sslip.io/#/edge-captures` → «Actualizar»: la captura de la demo aparece **arriba** (es la más reciente), con su foto, clase, confianza, ID, `edge01` y `1.0.0-int8.1`.
4. **Opcional, idempotencia en vivo (`200 duplicate`):** reenviar el mismo evento desde la laptop con el token de producción en la consola (`Read-Host -AsSecureString`, como en F5). Guardar la línea del evento como `evento_<ID>.json` y:
   ```powershell
   .\.venv\Scripts\python scripts\enviar_captura.py --reenviar --url https://174-129-84-80.sslip.io/api/p4/captures --foto <carpeta>\<ID>.jpg --evento <carpeta>\evento_<ID>.json
   ```
   Esperado: `HTTP 200` con `"status": "duplicate"` y el `received_at` original. Repetir la traza: el `VersionId` del registro **no cambia** y sigue habiendo 1 registro.

## Qué NO hacer

- **No provocar el fallo en AWS:** no tocar el security group, no detener la EC2, no parar contenedores, no cambiar el token del servidor ni el DNS. El fallo se provoca solo en la Pi y se revierte en la Pi.
- No usar una ruta inválida en el host correcto (ver arriba): la captura se pierde de la cola.
- No editar ni borrar `events.jsonl`, `pendientes.json` ni objetos de S3: son la evidencia.
- No mostrar en pantalla el token ni la contraseña de basic_auth.

## Cómo revertir si algo sale mal

| Situación | Acción |
|---|---|
| Quedó la ruta *blackhole* | `sudo ip route del blackhole 174.129.84.80` (o reiniciar la Pi) |
| Wi-Fi apagado | `sudo nmcli radio wifi on` |
| El programa quedó con `--url` inválida | `Ctrl+C` y arrancar sin `--url`; la cola se reenvía sola |
| `pendientes.json` no se vacía con red | Revisar `P4_DEVICE_TOKEN` (un `401` sale de la cola y no se reintenta) y que el portal responda (`curl.exe` del inicio) |
