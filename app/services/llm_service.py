from __future__ import annotations

import json
import os
import re
import unicodedata
from typing import Any

import requests


OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")


ORDER_KEYWORDS = (
    "necesita",
    "necesito",
    "enviar",
    "entregar",
    "pedido",
    "requiere",
    "solicita",
    "comprar",
)

UNIT_KEYWORDS = (
    "unidad",
    "unidades",
    "caja",
    "cajas",
    "paquete",
    "paquetes",
    "quintal",
    "quintales",
    "saco",
    "sacos",
    "botella",
    "botellas",
    "laptop",
    "laptops",
    "monitor",
    "monitores",
)


def normalize_text(text: str) -> str:
    text = text.lower().strip()
    text = unicodedata.normalize("NFD", text)
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


def is_valid_order_message(message: str) -> bool:
    text = normalize_text(message)

    order_words = [
        "necesito",
        "necesita",
        "necesite",
        "necesitar",
        "quiero",
        "quiere",
        "pido",
        "pide",
        "solicito",
        "solicita",
        "requiero",
        "requiere",
        "enviar",
        "enviame",
        "eviame",
        "mandame",
        "entregar",
    ]

    number_words = [
        "un",
        "una",
        "uno",
        "dos",
        "tres",
        "cuatro",
        "cinco",
        "seis",
        "siete",
        "ocho",
        "nueve",
        "diez",
    ]

    has_order_word = any(word in text for word in order_words)

    has_number = bool(re.search(r"\b\d+\b", text)) or any(
        re.search(rf"\b{word}\b", text) for word in number_words
    )

    return has_order_word and has_number


def replace_number_words(text: str) -> str:
    replacements = {
        " un ": " 1 ",
        " una ": " 1 ",
        " uno ": " 1 ",
        " dos ": " 2 ",
        " tres ": " 3 ",
        " cuatro ": " 4 ",
        " cinco ": " 5 ",
        " seis ": " 6 ",
        " siete ": " 7 ",
        " ocho ": " 8 ",
        " nueve ": " 9 ",
        " diez ": " 10 ",
    }

    result = f" {text} "
    for word, number in replacements.items():
        result = result.replace(word, number)

    return result.strip()


def empty_non_order(message: str) -> dict[str, Any]:
    return {
        "cliente": None,
        "telefono": None,
        "zona": None,
        "direccion": None,
        "productos": [],
        "urgencia": "media",
        "hora_limite": None,
        "observaciones": message,
        "estado": "mensaje_no_pedido",
        "score_prioridad": 0,
        "id": None,
        "errores": ["No se detectó un pedido válido. Indique producto y cantidad."],
    }


def build_prompt(message: str) -> str:
    return f"""
Extrae un pedido logístico y responde SOLO JSON válido.

Formato obligatorio:
{{"cliente":null,"telefono":null,"zona":null,"direccion":null,"productos":[],"urgencia":"media","hora_limite":null,"observaciones":"","estado":"pendiente_datos"}}

Reglas críticas:
- No inventes productos, cantidades, clientes, zonas ni direcciones.
- No copies datos de los ejemplos.
- Si el mensaje es saludo, texto casual o no contiene producto con cantidad, responde productos: [] y estado: "mensaje_no_pedido".
- Un pedido válido debe tener al menos una cantidad numérica y un producto.
- cliente: quien solicita el pedido.
- zona: lugar de entrega.
- productos: extrae todos los productos; conserva marcas y modelos en el nombre.
- si no existe unidad usa "unidades".
- urgencia: alta si contiene urgente/hoy/inmediato/rápido; baja si contiene sin prisa/próxima semana; caso contrario media.
- observaciones: copia el mensaje original.
- estado: recibido si hay cliente, zona y productos válidos; caso contrario pendiente_datos.

Ejemplo válido:
Entrada: TechZone necesita 5 laptops Lenovo y 3 monitores Samsung en Cumbayá urgente
Salida:
{{"cliente":"TechZone","telefono":null,"zona":"Cumbayá","direccion":null,"productos":[{{"nombre":"laptops Lenovo","cantidad":5,"unidad":"unidades"}},{{"nombre":"monitores Samsung","cantidad":3,"unidad":"unidades"}}],"urgencia":"alta","hora_limite":null,"observaciones":"TechZone necesita 5 laptops Lenovo y 3 monitores Samsung en Cumbayá urgente","estado":"recibido"}}

Ejemplo no pedido:
Entrada: Leonel necesita hola. Zona: Centro Histórico. Dirección: Mejía 533-461, 170401 Quito
Salida:
{{"cliente":null,"telefono":null,"zona":null,"direccion":null,"productos":[],"urgencia":"media","hora_limite":null,"observaciones":"Leonel necesita hola. Zona: Centro Histórico. Dirección: Mejía 533-461, 170401 Quito","estado":"mensaje_no_pedido"}}

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
        return empty_non_order(raw_response)


def normalize_order(order: dict[str, Any], original_message: str) -> dict[str, Any]:
    productos = order.get("productos")

    if not isinstance(productos, list):
        productos = []

    valid_products = []

    for producto in productos:
        if not isinstance(producto, dict):
            continue

        nombre = producto.get("nombre")
        cantidad = producto.get("cantidad")

        if not nombre or cantidad is None:
            continue

        try:
            cantidad = int(cantidad)
        except (TypeError, ValueError):
            continue

        if cantidad <= 0:
            continue

        unidad = producto.get("unidad") or "unidades"

        valid_products.append({
            "nombre": str(nombre).strip(),
            "cantidad": cantidad,
            "unidad": str(unidad).strip(),
        })

    if not is_valid_order_message(original_message):
        return empty_non_order(original_message)

    normalized = {
        "cliente": order.get("cliente"),
        "telefono": order.get("telefono"),
        "zona": order.get("zona"),
        "direccion": order.get("direccion"),
        "productos": valid_products,
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

    normalized["estado"] = "pendiente_datos" if missing else "recibido"
    normalized["errores"] = missing if missing else None

    return normalized


def extract_order_from_text(message: str) -> dict[str, Any]:
    if not is_valid_order_message(message):
        return empty_non_order(message)

    try:
        message = replace_number_words(message)
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