# Configuración Telegram + n8n

## Objetivo

Este documento describe la configuración del workflow de n8n para integrar Telegram con el backend FastAPI de LogistIA.

La integración permite recibir mensajes desde un bot de Telegram, procesarlos en n8n y consumir los endpoints existentes del backend para consultar estado, registrar pedidos y planificar despachos.

## Tecnologías utilizadas

- Telegram Bot
- n8n
- FastAPI
- ngrok
- Backend LogistIA

## Flujo general

```txt
Telegram
↓
n8n Telegram Trigger
↓
Switch Comandos
↓
HTTP Request
↓
FastAPI
↓
Respuesta al usuario por Telegram
```

## Comandos implementados

El bot reconoce los siguientes comandos mínimos:

```txt
/ayuda
/estado
/planificar
```

También se configuró un flujo fallback para registrar pedidos cuando el mensaje no coincide con los comandos anteriores.

## Endpoints consumidos

El workflow consume los siguientes endpoints existentes del backend FastAPI:

```txt
GET /api/status
POST /api/orders
POST /api/dispatch/plan
```

No se modificaron rutas, schemas ni servicios del backend para adaptar n8n.

## Estructura del workflow

El workflow contiene los siguientes nodos principales:

```txt
Telegram Trigger
Switch Comandos
GET Estado Backend
POST Crear Pedido
POST Planificar Despacho
Responder Ayuda
Responder Estado
Responder Pedido
Responder Planificacion
```

## Flujo de ayuda

Cuando el usuario envía:

```txt
/ayuda
```

n8n responde con un mensaje indicando los comandos disponibles y un ejemplo para registrar pedidos.

Flujo:

```txt
Telegram /ayuda
↓
Telegram Trigger
↓
Switch Comandos
↓
Responder Ayuda
```

## Flujo de estado

Cuando el usuario envía:

```txt
/estado
```

n8n consume el endpoint:

```txt
GET /api/status
```

y responde al usuario con el resumen del estado del sistema.

Flujo:

```txt
Telegram /estado
↓
Telegram Trigger
↓
Switch Comandos
↓
GET Estado Backend
↓
Responder Estado
```

Ejemplo de respuesta:

```txt
Estado del sistema:
{
  "recibido": 0,
  "pendientedatos": 0,
  "listoparadespacho": 0,
  "planificado": 0,
  "enruta": 0,
  "entregado": 0,
  "cancelado": 0
}
```

## Flujo de planificación

Cuando el usuario envía:

```txt
/planificar
```

n8n consume el endpoint:

```txt
POST /api/dispatch/plan
```

y responde al usuario con un resumen de la planificación generada.

Flujo:

```txt
Telegram /planificar
↓
Telegram Trigger
↓
Switch Comandos
↓
POST Planificar Despacho
↓
Responder Planificacion
```

Ejemplo de respuesta:

```txt
Planificacion lista

Pedidos: 1
Distancia total: 18.5 km
Tiempo estimado: 45 min
```

## Flujo de registro de pedido

Cuando el usuario envía un mensaje que no corresponde a `/ayuda`, `/estado` o `/planificar`, el workflow lo envía al endpoint de creación de pedidos.

Endpoint consumido:

```txt
POST /api/orders
```

Payload enviado:

```json
{
  "message": "<texto enviado por Telegram>"
}
```

Ejemplo de mensaje enviado por Telegram:

```txt
La señora Carmen necesita arroz urgente
```

Flujo:

```txt
Telegram
↓
n8n Telegram Trigger
↓
Switch Comandos
↓
POST Crear Pedido
↓
FastAPI responde JSON
↓
Responder Pedido
```

Ejemplo de respuesta:

```txt
Pedido registrado

Cliente: Carmen
Zona: La Magdalena
Urgencia: alta
Estado: recibido
ID: 10
```

## Configuración de nodos importantes

### Telegram Trigger

Este nodo recibe los mensajes enviados al bot de Telegram.

Debe estar conectado con las credenciales del bot configuradas en n8n.

No se deben subir tokens reales al repositorio.

### Switch Comandos

Este nodo evalúa el texto recibido desde Telegram.

Campo evaluado:

```js
$('Telegram Trigger').item.json.message.text
```

Reglas mínimas:

```txt
/ayuda
/estado
/planificar
```

Los mensajes que no coinciden con esos comandos pasan por el fallback hacia el flujo de creación de pedidos.

### GET Estado Backend

Configuración:

```txt
Method: GET
URL: http://127.0.0.1:8000/api/status
```

No requiere body.

### POST Crear Pedido

Configuración:

```txt
Method: POST
URL: http://127.0.0.1:8000/api/orders
Body Content Type: JSON
Specify Body: Using Fields Below
```

Body:

```txt
Name: message
Value: $('Telegram Trigger').item.json.message.text
```

El campo `Value` debe estar configurado como expresión.

### POST Planificar Despacho

Configuración:

```txt
Method: POST
URL: http://127.0.0.1:8000/api/dispatch/plan
Body Content Type: JSON
```

Este nodo consume el endpoint de planificación existente del backend.

### Responder Estado

Chat ID:

```js
$('Telegram Trigger').item.json.message.chat.id
```

Text:

```js
{{ "Estado del sistema:\n" + JSON.stringify($json, null, 2) }}
```

### Responder Pedido

Chat ID:

```js
$('Telegram Trigger').item.json.message.chat.id
```

Text:

```js
{{ "Pedido registrado\n\nCliente: " + $json.cliente + "\nZona: " + $json.zona + "\nUrgencia: " + $json.urgencia + "\nEstado: " + $json.estado + "\nID: " + $json.id }}
```

### Responder Planificacion

Chat ID:

```js
$('Telegram Trigger').item.json.message.chat.id
```

Text:

```js
{{ "Planificacion lista\n\nPedidos: " + $json.total_orders + "\nDistancia total: " + $json.route.total_distance_km + " km\nTiempo estimado: " + $json.route.total_time_min + " min" }}
```

## Configuración local

Para ejecutar el entorno local se utilizan tres terminales.

### Terminal 1: Backend FastAPI

Desde la raíz del proyecto:

```bash
py -m uvicorn app.main:app --reload
```

El backend queda disponible en:

```txt
http://127.0.0.1:8000
```

La documentación Swagger queda disponible en:

```txt
http://127.0.0.1:8000/docs
```

### Terminal 2: ngrok para n8n

```bash
ngrok http 5678
```

ngrok genera una URL HTTPS pública similar a:

```txt
https://ejemplo-ngrok.ngrok-free.dev
```

Esta URL se usa para que Telegram pueda comunicarse con n8n.

### Terminal 3: n8n

En CMD:

```cmd
set WEBHOOK_URL=https://TU_URL_DE_NGROK
n8n
```

En PowerShell:

```powershell
$env:WEBHOOK_URL="https://TU_URL_DE_NGROK"
n8n
```

El editor de n8n queda disponible en:

```txt
http://localhost:5678
```

## Consideraciones sobre ngrok

Para esta integración, ngrok debe apuntar al puerto de n8n:

```bash
ngrok http 5678
```

No debe apuntar al puerto 8000 para el flujo de Telegram, porque Telegram necesita llegar a n8n.

Como n8n y FastAPI corren en la misma computadora, los nodos HTTP Request pueden consumir el backend localmente mediante:

```txt
http://127.0.0.1:8000
```

## Seguridad

No se deben subir al repositorio:

```txt
Tokens reales de Telegram
Credenciales de n8n
Archivos .env
API keys
URLs privadas con credenciales
```

El workflow exportado no debe contener credenciales reales.

## Exportación del workflow

El workflow debe exportarse desde n8n y guardarse en:

```txt
n8n/workflow_logistiai.json
```

## Capturas recomendadas

Se recomienda documentar capturas de:

```txt
Workflow completo
Telegram Trigger
Switch Comandos
GET Estado Backend
POST Crear Pedido
POST Planificar Despacho
Responder Ayuda
Responder Estado
Responder Pedido
Responder Planificacion
Pruebas en Telegram
```

Antes de subir capturas, verificar que no aparezcan tokens ni credenciales.

## Observaciones de prueba

Durante las pruebas, el flujo Telegram -> n8n -> FastAPI funcionó correctamente.

El bot recibe mensajes desde Telegram, n8n enruta el flujo mediante el nodo Switch y consume los endpoints existentes del backend.

Se observó que el endpoint `POST /api/orders` puede responder con datos de ejemplo o fallback, como Carmen, La Magdalena y arroz, incluso cuando el mensaje enviado no contiene todos los datos. No se modificó el backend, ya que la responsabilidad del workflow es consumir los endpoints existentes.

## Archivos relacionados

```txt
n8n/workflow_logistiai.json
docs/n8n_telegram_setup.md
```