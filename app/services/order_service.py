from app.core.settings import (
    USE_MOCK_DB,
    USE_MOCK_LLM,
    USE_MOCK_ROUTING,
    USE_RULE_EXTRACTOR,
)

from app.core.logger import log_info, log_error
from app.services.validation_service import validate_order
from app.services.priority_service import calculate_priority
from app.services.rule_extractor_service import extract_order_with_rules
from app.services.inventory_service import validate_inventory, decrease_inventory

if USE_MOCK_LLM:
    from app.mocks.mock_llm import extract_order_from_text
else:
    from app.services.llm_service import extract_order_from_text


if USE_MOCK_DB:
    from app.mocks.mock_db import (
        save_order,
        get_all_orders,
        get_status_summary,
    )
else:
    from app.core.database import (
    save_order,
    get_all_orders,
    get_status_summary,
    update_order_status as update_order_status_db,
)

if USE_MOCK_ROUTING:
    from app.mocks.mock_routing import generate_mock_route
else:
    from app.services.routing_service import generate_route

def looks_like_order(message: str) -> bool:
    text = message.lower().strip()

    order_words = [
        "necesito",
        "necesita",
        "quiero",
        "quiere",
        "pido",
        "pide",
        "solicito",
        "solicita",
        "requiero",
        "requiere",
        "enviar",
        "entregar",
    ]

    has_order_word = any(word in text for word in order_words)
    has_number = any(char.isdigit() for char in text)

    return has_order_word and has_number

def process_order(message: str) -> dict:
    try:
        log_info("ORDER_PROCESS_STARTED", "Inicio del procesamiento de pedido")
        if not looks_like_order(message):
            log_info(
                "ORDER_IGNORED_NON_ORDER_MESSAGE",
                f"Mensaje ignorado porque no parece pedido: {message}",
            )

            return {
                "id": None,
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
                "errores": [
                    "No se detectó un pedido válido. Indique producto y cantidad."
                ],
            }
        if USE_RULE_EXTRACTOR:
            order_data = extract_order_with_rules(message)
            is_valid, errors = validate_order(order_data)

            if not is_valid:
                order_data = extract_order_from_text(message)
        else:
            order_data = extract_order_from_text(message)

        is_valid, errors = validate_order(order_data)

        if not is_valid:
            order_data["estado"] = "pendiente_datos"
            order_data["errores"] = errors
            order_data["score_prioridad"] = calculate_priority(order_data)

            saved_order = save_order(order_data)

            log_info(
                "ORDER_PENDING_DATA",
                f"Pedido guardado con datos pendientes. ID: {saved_order.get('id')}",
            )

            return saved_order

        inventory_errors = validate_inventory(order_data.get("productos", []))

        if inventory_errors:
           order_data["estado"] = "rechazado_stock"
           order_data["errores"] = inventory_errors
           order_data["score_prioridad"] = calculate_priority(order_data)

           log_info(
               "ORDER_REJECTED_STOCK",
               f"Pedido rechazado por stock insuficiente. Errores: {inventory_errors}",
            )

           return {
                "id": None,
                "cliente": order_data.get("cliente"),
                "telefono": order_data.get("telefono"),
                "zona": order_data.get("zona"),
                "direccion": order_data.get("direccion"),
                "productos": order_data.get("productos", []),
                "urgencia": order_data.get("urgencia"),
                "hora_limite": order_data.get("hora_limite"),
                "observaciones": order_data.get("observaciones"),
                "estado": "rechazado_stock",
                "score_prioridad": order_data.get("score_prioridad"),
                "errores": inventory_errors,
            }

        order_data["estado"] = "recibido"
        order_data["score_prioridad"] = calculate_priority(order_data)
        order_data["errores"] = None
        decrease_inventory(order_data.get("productos", []))

        saved_order = save_order(order_data)

        log_info(
            "ORDER_CREATED",
            f"Pedido creado correctamente. ID: {saved_order.get('id')}",
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
            f"Consulta de pedidos realizada. Total: {len(orders)}",
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
            "Resumen de estados consultado",
        )

        return status

    except Exception as e:
        log_error("STATUS_SUMMARY_ERROR", str(e))
        raise


def generate_dispatch_plan() -> dict:
    try:
        orders = get_all_orders()
        ready_orders = [
            order
            for order in orders
            if order.get("estado") == "listo_para_despacho"
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
                destination_zones=destination_zones,
            )

        log_info(
            "DISPATCH_PLAN_GENERATED",
            f"Plan de despacho generado. Pedidos incluidos: {len(ready_orders)}",
        )

        return {
            "total_orders": len(ready_orders),
            "route": route,
            "message": "Plan de despacho generado",
        }

    except Exception as e:
        log_error("DISPATCH_PLAN_ERROR", str(e))
        raise

def update_order_status(order_id: int, estado: str) -> dict:
    estados_validos = {
        "recibido",
        "pendiente_datos",
        "listo_para_despacho",
        "planificado",
        "en_ruta",
        "entregado",
        "cancelado",
    }

    try:
        if estado not in estados_validos:
            raise ValueError(f"Estado inválido: {estado}")

        updated_order = update_order_status_db(order_id, estado)

        log_info(
            "ORDER_STATUS_UPDATED",
            f"Pedido {order_id} actualizado a estado {estado}",
        )

        return updated_order

    except Exception as e:
        log_error("ORDER_STATUS_UPDATE_ERROR", str(e))
        raise