# Crea el endpoint POST /api/orders

# Ahora guarda el pedido en mock DB.
from fastapi import APIRouter

from app.schemas.order_schema import (
    OrderRequestSchema,
    OrderResponseSchema
)

from app.services.order_service import (
    process_order,
    list_orders,
    get_status,
    generate_dispatch_plan
)


router = APIRouter(
    prefix="/api",
    tags=["Orders"]
)


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