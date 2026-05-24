# Orquestacion llama al mock -> valida campos -> asigna estados -> calcula prioridad ->guarda mock en BD ->genra el plan

#Anterior
from app.core.settings import (
    USE_MOCK_DB,
    USE_MOCK_LLM,
    USE_MOCK_ROUTING
)

from app.core.logger import log_info, log_error
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
    try:
        log_info("ORDER_PROCESS_STARTED", "Inicio del procesamiento de pedido")

        order_data = extract_order_from_text(message)

        is_valid, errors = validate_order(order_data)

        if not is_valid:
            order_data["estado"] = "pendiente_datos"
            order_data["errores"] = errors

            saved_order = save_order(order_data)

            log_info(
                "ORDER_PENDING_DATA",
                f"Pedido guardado con datos pendientes. ID: {saved_order.get('id')}"
            )

            return saved_order

        order_data["estado"] = "recibido"
        order_data["score_prioridad"] = calculate_priority(order_data)
        order_data["errores"] = None

        saved_order = save_order(order_data)

        log_info(
            "ORDER_CREATED",
            f"Pedido creado correctamente. ID: {saved_order.get('id')}"
        )

        return saved_order

    except Exception as e:
        log_error("ORDER_PROCESS_ERROR", str(e))
        raise


def list_orders() -> list[dict]:
    try:
        orders = get_all_orders()

        log_info(
            "ORDERS_LISTED",
            f"Consulta de pedidos realizada. Total: {len(orders)}"
        )

        return orders

    except Exception as e:
        log_error("ORDERS_LIST_ERROR", str(e))
        raise


def get_status() -> dict:
    try:
        status = get_status_summary()

        log_info(
            "STATUS_SUMMARY_REQUESTED",
            "Resumen de estados consultado"
        )

        return status

    except Exception as e:
        log_error("STATUS_SUMMARY_ERROR", str(e))
        raise


def generate_dispatch_plan() -> dict:
    try:
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

        log_info(
            "DISPATCH_PLAN_GENERATED",
            f"Plan de despacho generado. Pedidos incluidos: {len(ready_orders)}"
        )

        return {
            "total_orders": len(ready_orders),
            "route": route,
            "message": "Plan de despacho generado"
        }

    except Exception as e:
        log_error("DISPATCH_PLAN_ERROR", str(e))
        raise