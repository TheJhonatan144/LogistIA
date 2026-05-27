from __future__ import annotations

import json
import os
from typing import Any

import requests


OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")


def build_prompt(message: str) -> str:
    return f"""
Eres un extractor de pedidos logísticos para LogistiAI.

Devuelve SOLO JSON válido. No expliques nada.

Formato obligatorio:
{{
  "cliente": string | null,
  "telefono": string | null,
  "zona": string | null,
  "direccion": string | null,
  "productos": [
    {{
      "nombre": string,
      "cantidad": number | null,
      "unidad": string | null
    }}
  ],
  "urgencia": "alta" | "media" | "baja" | null,
  "hora_limite": string | null,
  "observaciones": string | null,
  "estado": "recibido" | "pendiente_datos"
}}

Reglas:
- No inventes datos.
- Si falta un dato, usa null.
- Si no hay productos claros, usa [].
- Detecta urgencia si aparecen palabras como urgente, rápido, hoy, inmediato.
- Si no hay urgencia explícita, usa "media".
- El cliente normalmente aparece antes de palabras como "necesita", "pide", "pidió", "quiere" o "solicita".
- La zona normalmente aparece después de palabras como "en", "sector", "zona", "barrio" o "desde".
- En frases como "20 cajas de galletas", la unidad es "cajas" y el producto es "galletas".
- No incluyas la unidad dentro del nombre del producto.
- Conserva el mensaje original en observaciones.
Mensaje:
{message}
""".strip()


def call_ollama(prompt: str) -> str:
    response = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
        },
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    return data.get("response", "")


def safe_parse_json(raw_response: str) -> dict[str, Any]:
    try:
        start = raw_response.find("{")
        end = raw_response.rfind("}") + 1

        if start == -1 or end == 0:
            raise ValueError("No se encontró JSON válido en la respuesta.")

        clean_json = raw_response[start:end]
        return json.loads(clean_json)

    except Exception:
        return {
            "cliente": None,
            "telefono": None,
            "zona": None,
            "direccion": None,
            "productos": [],
            "urgencia": "media",
            "hora_limite": None,
            "observaciones": raw_response,
            "estado": "pendiente_datos",
            "errores": ["respuesta_llm_invalida"],
        }


def normalize_order(order: dict[str, Any], original_message: str) -> dict[str, Any]:
    productos = order.get("productos")

    if not isinstance(productos, list):
        productos = []

    for producto in productos:
        if not isinstance(producto, dict):
            continue

        unidad = producto.get("unidad")
        nombre = producto.get("nombre")

        if unidad in (None, "", "null"):
            if nombre:
                producto["unidad"] = "unidades"

    normalized = {
        "cliente": order.get("cliente"),
        "telefono": order.get("telefono"),
        "zona": order.get("zona"),
        "direccion": order.get("direccion"),
        "productos": productos,
        "urgencia": order.get("urgencia") or "media",
        "hora_limite": order.get("hora_limite"),
        "observaciones": order.get("observaciones") or original_message,
    }

    missing = []

    if not normalized["cliente"]:
        missing.append("cliente")

    if not normalized["zona"]:
        missing.append("zona")

    if not normalized["productos"]:
        missing.append("productos")
    else:
        for index, product in enumerate(normalized["productos"], start=1):
            if not product.get("nombre"):
                missing.append(f"producto_{index}_nombre")

            if product.get("cantidad") is None:
                missing.append(f"producto_{index}_cantidad")

            if not product.get("unidad"):
                missing.append(f"producto_{index}_unidad")

    normalized["estado"] = "pendiente_datos" if missing else "recibido"
    normalized["errores"] = missing if missing else None

    return normalized

def extract_order_from_text(message: str) -> dict[str, Any]:
    try:
        prompt = build_prompt(message)
        raw_response = call_ollama(prompt)
        parsed = safe_parse_json(raw_response)
        return normalize_order(parsed, message)

    except requests.exceptions.RequestException as exc:
        return {
            "cliente": None,
            "telefono": None,
            "zona": None,
            "direccion": None,
            "productos": [],
            "urgencia": "media",
            "hora_limite": None,
            "observaciones": message,
            "estado": "pendiente_datos",
            "errores": [f"ollama_no_disponible: {exc}"],
        }