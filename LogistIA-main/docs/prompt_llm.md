# Prompt LLM - LogistiAI

## Descripción

Este módulo utiliza un modelo de lenguaje local (Ollama + Qwen) para convertir pedidos en lenguaje natural en datos estructurados en formato JSON.

El objetivo es transformar mensajes informales (por ejemplo desde Telegram) en información que el sistema pueda procesar automáticamente.

---

## Función principal

```python
extract_order_from_text(text: str) -> dict
```

Recibe un texto en lenguaje natural y devuelve un diccionario estructurado con los datos del pedido.

---

## Estructura de salida

```json
{
  "cliente": "string | null",
  "zona": "string | null",
  "productos": [
    {
      "nombre": "string",
      "cantidad": "number | null",
      "unidad": "string | null"
    }
  ],
  "urgencia": null,
  "estado": "recibido | pendiente_datos"
}
```

---

## Reglas del prompt

El modelo sigue las siguientes reglas:

- Responde únicamente en formato JSON válido
- No incluye explicaciones adicionales
- No inventa datos faltantes
- Usa `null` cuando no existe información
- Usa `[]` si no hay productos claros
- Separa correctamente cliente y zona
- Convierte cantidades explícitas ("una", "dos", etc.)
- No interpreta urgencia (se maneja en otro módulo)

---

## Ejemplo

### Entrada

```
La señora Carmen de La Magdalena necesita 2 quintales de arroz y una caja de aceite.
```

### Salida

```json
{
  "cliente": "Carmen",
  "zona": "La Magdalena",
  "productos": [
    {
      "nombre": "arroz",
      "cantidad": 2,
      "unidad": "quintales"
    },
    {
      "nombre": "aceite",
      "cantidad": 1,
      "unidad": "caja"
    }
  ],
  "urgencia": null,
  "estado": "recibido"
}
```

---

## Integración en el sistema

```
Telegram → n8n → FastAPI → LLM → planificación → ruteo
```

El LLM recibe el texto del pedido y devuelve un JSON que es utilizado por el backend para:

- Validación de pedidos
- Almacenamiento en base de datos
- Cálculo de prioridad
- Planificación de despacho

---

## Notas

- El modelo utilizado es `qwen2.5:7b` ejecutado localmente con Ollama
- No se requiere conexión a internet
- Se mantiene un enfoque modular para facilitar reemplazo del LLM
