# Base de datos temporal en memoria

orders = []


def save_order(order: dict) -> dict:
    order_id = len(orders) + 1
    order["id"] = order_id
    orders.append(order)
    return order


def get_all_orders() -> list[dict]:
    return orders


def get_status_summary() -> dict:
    summary = {
        "recibido": 0,
        "pendiente_datos": 0,
        "listo_para_despacho": 0,
        "planificado": 0,
        "en_ruta": 0,
        "entregado": 0,
        "cancelado": 0
    }

    for order in orders:
        status = order.get("estado", "recibido")
        if status in summary:
            summary[status] += 1

    return summary