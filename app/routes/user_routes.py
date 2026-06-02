from fastapi import APIRouter, HTTPException
import sqlite3
from pathlib import Path

router = APIRouter(prefix="/api/users", tags=["Users"])

DB_PATH = Path("data/logistiai.db")

MENUS_FINALES_TELEGRAM = {
    "duenio": [
        "📊 Dashboard",
        "📦 Ver Pedidos",
    ],
    "chofer": [
        "🚚 Mis Entregas",
        "🚨 Alerta",
    ],
    "cliente": [
        "📝 Nuevo Pedido",
        "🔎 Mi Estado",
    ],
    "bodega": [
        "📥 Pedidos recibidos",
        "⚠️ Alertas de stock",
        "📊 Inventario",
    ],
}

@router.get("/telegram/{telegram_id}")
def get_user_by_telegram_id(telegram_id: str):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                id,
                telegram_id,
                nombre,
                rol,
                activo,
                zona,
                direccion,
                maps_url
            FROM usuarios
            WHERE telegram_id = ? AND activo = 1
            """,
            (telegram_id,),
        )

        user = cursor.fetchone()

        if not user:
            raise HTTPException(status_code=403, detail="Usuario no autorizado")

        user = dict(user)

        return {
            "id": user["id"],
            "telegram_id": user["telegram_id"],
            "nombre": user["nombre"],
            "rol": user["rol"],
            "zona": user["zona"],
            "direccion": user["direccion"],
            "maps_url": user["maps_url"],
            "menu": MENUS_FINALES_TELEGRAM.get(user["rol"], []),
        }

    finally:
        conn.close()