import sqlite3
import re
from pathlib import Path
from difflib import SequenceMatcher

DB_PATH = Path("data/logistiai.db")


def _normalize(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-záéíóúñ0-9 ]", "", text)

    replacements = {
        "laptops": "laptop",
        "monitores": "monitor",
        "impresoras": "impresora",
        "teclados": "teclado",
        "mouses": "mouse",
        "routers": "router",
        "discos": "disco",
        "cables": "cable",
    }

    for plural, singular in replacements.items():
        text = text.replace(plural, singular)

    return text


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, _normalize(a), _normalize(b)).ratio()


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
        best_score = 0

        for product in products:
            score = max(
                _similarity(product_name, product["nombre"]),
                _similarity(product_name, product["sku"]),
            )

            if score > best_score:
                best_score = score
                best_match = product

        if best_score < 0.40:
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