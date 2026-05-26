import requests
import json
import os

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")


def build_prompt(text: str) -> str:
    return f"""
Eres un extractor de pedidos logísticos.

Responde SOLO JSON válido.

Reglas:
- No expliques nada
- No agregues texto fuera del JSON
- No inventes datos
- Si un dato no está presente, usar null
- Si no hay productos claros, usar []
- Ignora cualquier indicación de urgencia en el mensaje
- Separa correctamente el nombre del cliente y la zona (ejemplo: "Carmen de La Magdalena" → cliente: "Carmen", zona: "La Magdalena")

Reglas de cantidades:
- Convierte "un", "una" en cantidad = 1
- Convierte números escritos en palabras ("dos", "tres", etc.) a números
- Si la cantidad es ambigua ("varios", "algunos", "unas cuantas", "un par", etc.), usar null
- No inventar cantidades si no están claras

Formato:
{{
  "cliente": string | null,
  "zona": string | null,
  "productos": [
    {{
      "nombre": string,
      "cantidad": number | null,
      "unidad": string | null
    }}
  ],
  "urgencia": null,
  "estado": "recibido" | "pendiente_datos"
}}

Mensaje:
{text}
"""


def call_ollama(prompt: str) -> str:
    response = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False
        }
    )

    return response.json()["response"]


def safe_parse_json(raw: str) -> dict:
    try:
        return json.loads(raw)
    except Exception:
        return {
            "error": "json_invalido",
            "raw_response": raw
        }


def detect_missing_fields(order: dict) -> list:
    missing = []

    if not order.get("cliente"):
        missing.append("cliente")

    if not order.get("zona"):
        missing.append("zona")

    if not order.get("productos"):
        missing.append("productos")

    return missing


def extract_order_from_text(text: str) -> dict:
    prompt = build_prompt(text)

    raw_response = call_ollama(prompt)

    parsed = safe_parse_json(raw_response)

    if "error" in parsed:
        return parsed

    missing = detect_missing_fields(parsed)

    if missing:
        parsed["estado"] = "pendiente_datos"
    else:
        parsed["estado"] = "recibido"

    return parsed