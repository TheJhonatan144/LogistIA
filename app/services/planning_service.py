from app.services.priority_service import calculate_priority


PLANNABLE_STATUS = "listo_para_despacho"
TEMP_TEST_STATUS = "recibido"


def group_orders_by_zone(orders: list[dict]) -> dict:
    """
    Agrupa pedidos por zona.
    Si no existe zona, usa 'Sin zona'.
    """

    zones = {}

    for order in orders:
        zone = order.get("zona") or "Sin zona"

        if zone not in zones:
            zones[zone] = []

        zones[zone].append(order)

    return zones


def sort_orders_by_priority(orders: list[dict]) -> list[dict]:
    """
    Ordena pedidos por score_prioridad de mayor a menor.
    Si el pedido no tiene score, lo calcula.
    """

    orders_with_score = []

    for order in orders:
        order_copy = order.copy()

        if order_copy.get("score_prioridad") is None:
            order_copy["score_prioridad"] = calculate_priority(order_copy)
        else:
            order_copy["score_prioridad"] = calculate_priority(order_copy)

        orders_with_score.append(order_copy)

    return sorted(
        orders_with_score,
        key=lambda order: (
            order.get("score_prioridad", 0),
            -order.get("id", 0)
        ),
        reverse=True
    )


def generate_dispatch_plan(orders: list[dict]) -> dict:
    """
    Genera plan de despacho:
    - filtra pedidos listos para despacho;
    - permite 'recibido' temporalmente para pruebas mock;
    - calcula score;
    - ordena por prioridad;
    - agrupa por zona;
    - genera explicación textual.
    """

    plannable_orders = [
        order for order in orders
        if order.get("estado") in [PLANNABLE_STATUS, TEMP_TEST_STATUS]
    ]

    ordered_orders = sort_orders_by_priority(plannable_orders)
    zones = group_orders_by_zone(ordered_orders)

    plan = {
        "total_orders": len(ordered_orders),
        "zones": zones,
        "ordered_orders": ordered_orders,
        "explanation": ""
    }

    plan["explanation"] = explain_dispatch_plan(plan)

    return plan


def explain_dispatch_plan(plan: dict) -> str:
    """
    Explica el plan de despacho de forma simple y entendible.
    """

    total_orders = plan.get("total_orders", 0)
    zones = plan.get("zones", {})

    if total_orders == 0:
        return "No existen pedidos listos para despacho."

    zone_names = list(zones.keys())
    zone_count = len(zone_names)

    top_order = None

    ordered_orders = plan.get("ordered_orders", [])

    if ordered_orders:
        top_order = ordered_orders[0]

    explanation = (
        f"Se planificaron {total_orders} pedido(s) "
        f"agrupados en {zone_count} zona(s). "
        "Los pedidos fueron ordenados por score de prioridad, "
        "considerando urgencia, tipo de cliente, zona, restricción horaria "
        "y valor operativo."
    )

    if top_order:
        explanation += (
            f" El pedido con mayor prioridad es el #{top_order.get('id')} "
            f"de {top_order.get('cliente')} en {top_order.get('zona')}, "
            f"con score {top_order.get('score_prioridad')}."
        )

    explanation += (
        " Esta planificación no calcula rutas reales; deja los pedidos "
        "organizados para que Routing Service genere distancia, tiempo y recorrido."
    )

    return explanation
