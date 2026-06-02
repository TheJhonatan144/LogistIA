# Crea el endpoint POST /api/orders

# Ahora guarda el pedido en mock DB.
from fastapi import APIRouter
from pydantic import BaseModel
import sqlite3

from app.schemas.order_schema import (
    OrderRequestSchema,
    OrderResponseSchema
)

from app.services.order_service import (
    process_order,
    list_orders,
    get_status,
    generate_dispatch_plan,
    update_order_status
)


router = APIRouter(
    prefix="/api",
    tags=["Orders"]
)
class OrderStatusUpdateSchema(BaseModel):
    estado: str

@router.post(
    "/orders",
    response_model=OrderResponseSchema
)
def create_order(order: OrderRequestSchema):
    return process_order(order.message)


@router.get("/orders")
def get_orders():
    return {
        "orders": list_orders()
    }


@router.get("/status")
def status():
    return get_status()


@router.post("/dispatch/plan")
def dispatch_plan():
    return generate_dispatch_plan()
@router.patch("/orders/{order_id}/status")
def update_status(
    order_id: int,
    payload: OrderStatusUpdateSchema
):
    return update_order_status(
        order_id,
        payload.estado
    )
@router.get("/inventory")
def get_inventory():

    conn = sqlite3.connect("data/logistiai.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            p.id,
            p.sku,
            p.nombre,
            p.categoria,
            i.stock,
            i.stock_minimo
        FROM inventario i
        JOIN productos p
            ON p.id = i.producto_id
        WHERE p.activo = 1
        ORDER BY p.categoria, p.nombre
    """)

    rows = cursor.fetchall()

    conn.close()

    return {
        "inventory": [
            {
                "id": row[0],
                "sku": row[1],
                "nombre": row[2],
                "categoria": row[3],
                "stock": row[4],
                "stock_minimo": row[5],
                "stock_bajo": row[4] <= row[5]
            }
            for row in rows
        ]
    }