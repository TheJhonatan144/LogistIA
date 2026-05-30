from __future__ import annotations

import json
import os
from typing import Any

import requests


OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
# OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")


def build_prompt(message: str) -> str:
    return f"""
Extrae un pedido logístico y responde SOLO JSON válido.

Formato:
{{"cliente":null,"telefono":null,"zona":null,"direccion":null,"productos":[{{"nombre":null,"cantidad":null,"unidad":"unidades"}}],"urgencia":"media","hora_limite":null,"observaciones":"","estado":"recibido"}}

Reglas:
- cliente: quien solicita el pedido.
- zona: lugar de entrega.
- productos: extrae todos los productos; conserva marcas y modelos en el nombre.
- si no existe unidad usa "unidades".
- urgencia: alta si contiene urgente/hoy/inmediato/rápido; baja si contiene sin prisa/próxima semana; caso contrario media.
- observaciones: copia el mensaje original.
- estado: recibido si hay cliente, zona y productos; caso contrario pendiente_datos.

Ejemplo:
TechZone necesita 5 laptops Lenovo y 3 monitores Samsung en Cumbayá urgente

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
        timeout=120,
    )
    response.raise_for_status()
    data = response.json()
    return data.get("response", "")


def safe_parse_json(raw_response: str) -> dict[str, Any]:
    try:
        clean = raw_response.strip()
        if clean.startswith("```"):
            lines = clean.splitlines()
            clean = "\n".join(
                line for line in lines
                if not line.strip().startswith("```")
            )

        start = clean.find("{")
        end = clean.rfind("}") + 1

        if start == -1 or end == 0:
            raise ValueError("No se encontró JSON en la respuesta.")

        return json.loads(clean[start:end])

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
        if producto.get("unidad") in (None, "", "null") and producto.get("nombre"):
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
        for i, p in enumerate(normalized["productos"], start=1):
            if not p.get("nombre"):
                missing.append(f"producto_{i}_nombre")
            if p.get("cantidad") is None:
                missing.append(f"producto_{i}_cantidad")
            if not p.get("unidad"):
                missing.append(f"producto_{i}_unidad")

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