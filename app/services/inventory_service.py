import sqlite3
import re
from pathlib import Path
from difflib import SequenceMatcher

DB_PATH = Path("data/logistiai.db")


def _normalize(text: str) -> str:
    if not text:
        return ""

    text = text.lower().strip()

    replacements = {
        "á": "a",
        "é": "e",
        "í": "i",
        "ó": "o",
        "ú": "u",
        "ñ": "n",
        "-": " ",
        "_": " ",
        ".": " ",
        ",": " ",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    word_replacements = {
        "laptops": "laptop",
        "notebooks": "laptop",
        "computadoras": "laptop",
        "monitores": "monitor",
        "pantallas": "monitor",
        "impresoras": "impresora",
        "teclados": "teclado",
        "mouses": "mouse",
        "ratones": "mouse",
        "routers": "router",
        "ruters": "router",
        "discos": "disco",
        "cables": "cable",
    }

    words = re.sub(r"[^a-z0-9 ]", " ", text).split()
    words = [word_replacements.get(word, word) for word in words]

    aliases = {
        "tplink": "tp link",
        "tp-link": "tp link",
        "tp_link": "tp link",
        "logitec": "logitech",
        "sansung": "samsung",
        "hewlett": "hp",
        "packard": "hp",
    }

    text = " ".join(words)

    for old, new in aliases.items():
        text = text.replace(old, new)

    text = re.sub(r"\s+", " ", text).strip()
    return text


def _compact(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", _normalize(text))


def _similarity(a: str, b: str) -> float:
    norm_a = _normalize(a)
    norm_b = _normalize(b)

    compact_a = _compact(a)
    compact_b = _compact(b)

    if not norm_a or not norm_b:
        return 0.0

    if compact_a == compact_b:
        return 1.0

    if compact_a in compact_b or compact_b in compact_a:
        return 0.92

    return max(
        SequenceMatcher(None, norm_a, norm_b).ratio(),
        SequenceMatcher(None, compact_a, compact_b).ratio(),
    )


def find_product_by_name(product_name: str) -> dict | None:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                p.id,
                p.sku,
                p.nombre,
                p.categoria,
                i.stock,
                i.stock_minimo
            FROM productos p
            JOIN inventario i ON p.id = i.producto_id
            WHERE p.activo = 1
        """)

        products = [dict(row) for row in cursor.fetchall()]

        best_match = None
        best_score = 0.0

        for product in products:
            score_nombre = _similarity(product_name, product["nombre"])
            score_sku = _similarity(product_name, product["sku"] or "")
            score = max(score_nombre, score_sku)

            if score > best_score:
                best_score = score
                best_match = product

        if best_score < 0.78:
            return None

        return best_match

    finally:
        conn.close()


def validate_inventory(order_products: list[dict]) -> list[str]:
    errors = []

    for item in order_products:
        product_name = item.get("nombre")
        quantity = item.get("cantidad")

        if not product_name:
            errors.append("Producto sin nombre")
            continue

        if quantity is None:
            errors.append(f"Falta cantidad para {product_name}")
            continue

        inventory_product = find_product_by_name(product_name)

        if not inventory_product:
            errors.append(f"Producto no registrado en inventario: {product_name}")
            continue

        if int(quantity) > int(inventory_product["stock"]):
            errors.append(
                f"Stock insuficiente para {inventory_product['nombre']}. "
                f"Solicitado: {int(quantity)}. "
                f"Disponible: {inventory_product['stock']}."
            )

    return errors


def decrease_inventory(order_products: list[dict]) -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        cursor = conn.cursor()

        for item in order_products:
            product_name = item.get("nombre")
            quantity = item.get("cantidad")

            if not product_name or quantity is None:
                continue

            inventory_product = find_product_by_name(product_name)

            if not inventory_product:
                continue

            cursor.execute(
                """
                UPDATE inventario
                SET stock = stock - ?
                WHERE producto_id = ?
                """,
                (int(quantity), inventory_product["id"]),
            )

        conn.commit()

    finally:
        conn.close()