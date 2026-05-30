import re

def normalize_zone(zone: str | None) -> str | None:
    if not zone:
        return None

    clean = zone.strip()

    replacements = {
        "Cumbaya": "Cumbayá",
        "cumbaya": "Cumbayá",
        "Tumbaco": "Tumbaco",
        "tumbaco": "Tumbaco",
    }

    return replacements.get(clean, clean)
def extract_order_with_rules(message: str) -> dict:
    text = message.strip()

    urgency = "media"
    lower = text.lower()

    if any(word in lower for word in [
        "urgente",
        "hoy",
        "inmediato",
        "rápido",
        "rapido"
    ]):
        urgency = "alta"

    elif any(word in lower for word in [
        "sin prisa",
        "próxima semana",
        "proxima semana"
    ]):
        urgency = "baja"

    zone = None

    zone_match = re.search(
        r"\b(?:en|sector|zona|barrio)\s+([A-Za-zÁÉÍÓÚáéíóúÑñ\s]+?)(?:\s+urgente|\s+hoy|\s+inmediato|$)",
        text,
        re.IGNORECASE
    )

    if zone_match:
        zone = normalize_zone(zone_match.group(1))

    client = None

    client_match = re.search(
        r"^(.+?)\s+(?:necesita|pide|quiere|solicita|requiere)\s+",
        text,
        re.IGNORECASE
    )

    if client_match:
        client = client_match.group(1).strip()

    product_text = text

    product_text = re.sub(
        r"^.+?\s+(?:necesita|pide|quiere|solicita|requiere)\s+",
        "",
        product_text,
        flags=re.IGNORECASE
    )

    product_text = re.sub(
        r"\b(?:en|sector|zona|barrio)\s+[A-Za-zÁÉÍÓÚáéíóúÑñ\s]+?(?:\s+urgente|\s+hoy|\s+inmediato|$)",
        "",
        product_text,
        flags=re.IGNORECASE
    )

    product_text = re.sub(
        r"\b(urgente|hoy|inmediato|rápido|rapido)\b",
        "",
        product_text,
        flags=re.IGNORECASE
    )

    parts = re.split(r"\s+y\s+|,\s*", product_text)

    products = []

    for part in parts:
        part = part.strip()

        match = re.search(r"(\d+)\s+(.+)", part)

        if not match:
            continue

        quantity = int(match.group(1))
        name = match.group(2).strip()

        products.append({
            "nombre": name,
            "cantidad": quantity,
            "unidad": "unidades"
        })

    return {
        "cliente": client,
        "telefono": None,
        "zona": zone,
        "direccion": None,
        "productos": products,
        "urgencia": urgency,
        "hora_limite": None,
        "observaciones": message,
        "estado": (
            "recibido"
            if client and zone and products
            else "pendiente_datos"
        ),
        "errores": None
    }