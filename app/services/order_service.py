# Orquestacion llama al mock -> valida campos -> asigna estados -> calcula prioridad ->guarda mock en BD ->genra el plan
from app.core.settings import (
    USE_MOCK_DB,
    USE_MOCK_LLM,
    USE_MOCK_ROUTING
)

from app.services.validation_service import validate_order
from app.services.priority_service import calculate_priority


if USE_MOCK_LLM:
    from app.mocks.mock_llm import extract_order_from_text
else:
    from app.services.llm_service import extract_order_from_text


if USE_MOCK_DB:
    from app.mocks.mock_db import (
        save_order,
        get_all_orders,
        get_status_summary
    )
else:
    from app.core.database import (
        save_order,
        get_all_orders,
        get_status_summary
    )


if USE_MOCK_ROUTING:
    from app.mocks.mock_routing import generate_mock_route
else:
    from app.services.routing_service import generate_route


def process_order(message: str) -> dict:
    order_data = extract_order_from_text(message)

    is_valid, errors = validate_order(order_data)

    if not is_valid:
        order_data["estado"] = "pendiente_datos"
        order_data["errores"] = errors
        return save_order(order_data)

    order_data["estado"] = "recibido"
    order_data["score_prioridad"] = calculate_priority(order_data)
    order_data["errores"] = None

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

    if USE_MOCK_ROUTING:
        route = generate_mock_route(ready_orders)
    else:
        destination_zones = list({
            order.get("zona")
            for order in ready_orders
            if order.get("zona")
        })

        route = generate_route(
            origin_zone="El Girón",
            destination_zones=destination_zones
        )

    return {
        "total_orders": len(ready_orders),
        "route": route,
        "message": "Plan de despacho generado"
    }