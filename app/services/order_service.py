# Orquestacion llama al mock -> valida campos -> asigna estados -> calcula prioridad ->guarda mock en BD ->genra el plan
from app.mocks.mock_llm import extract_order_from_text
from app.mocks.mock_db import (
    save_order,
    get_all_orders,
    get_status_summary
)
from app.mocks.mock_routing import generate_mock_route

from app.services.validation_service import validate_order
from app.services.priority_service import calculate_priority


def process_order(message: str) -> dict:
    order_data = extract_order_from_text(message)

    is_valid, errors = validate_order(order_data)

    if not is_valid:
        order_data["estado"] = "pendiente_datos"
        order_data["errores"] = errors
        return save_order(order_data)

    order_data["estado"] = "recibido"
    order_data["score_prioridad"] = calculate_priority(order_data)

    return save_order(order_data)


def list_orders() -> list[dict]:
    return get_all_orders()


def get_status() -> dict:
    return get_status_summary()


def generate_dispatch_plan() -> dict:
    orders = get_all_orders()
    ready_orders = [
        order for order in orders
        if order.get("estado") in ["recibido", "listo_para_despacho"]
    ]

    route = generate_mock_route(ready_orders)

    return {
        "total_orders": len(ready_orders),
        "route": route,
        "message": "Plan de despacho generado con datos simulados"
    }