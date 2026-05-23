URGENCY_SCORE = {
    "alta": 100,
    "media": 60,
    "baja": 30
}

CLIENT_TYPE_SCORE = {
    "vip": 100,
    "normal": 50
}

DEFAULT_ZONE_SCORE = 70
DEFAULT_ORDER_VALUE_SCORE = 50


def calculate_priority(order: dict) -> int:
    """
    Calcula un score de prioridad entre 0 y 100.

    Criterios usados:
    - urgencia del pedido;
    - tipo de cliente;
    - cercanía/zona;
    - valor operativo aproximado;
    - restricción horaria;
    - posibilidad de agrupación por zona;
    - penalización por errores.
    """

    urgencia = (order.get("urgencia") or "baja").lower()
    tipo_cliente = (order.get("tipo_cliente") or "normal").lower()

    urgency_score = URGENCY_SCORE.get(urgencia, 30)
    client_score = CLIENT_TYPE_SCORE.get(tipo_cliente, 50)

    zone_score = _calculate_zone_score(order)
    order_value_score = _calculate_order_value_score(order)

    score = (
        urgency_score * 0.40 +
        client_score * 0.25 +
        zone_score * 0.20 +
        order_value_score * 0.15
    )

    if order.get("hora_limite"):
        score += 10

    observaciones = (order.get("observaciones") or "").lower()

    if "urgente" in observaciones or "prioridad" in observaciones:
        score += 5

    if order.get("errores"):
        score -= 30

    score = max(0, min(100, round(score)))

    return score


def _calculate_zone_score(order: dict) -> int:
    """
    Estima cercanía o conveniencia de zona para el MVP.
    No calcula rutas reales.
    """

    zona = (order.get("zona") or "").lower()

    zonas_cercanas = [
        "el girón",
        "la carolina",
        "centro",
        "centro histórico",
        "la magdalena"
    ]

    zonas_medias = [
        "norte",
        "sur",
        "el condado",
        "calderón",
        "carapungo"
    ]

    if zona in zonas_cercanas:
        return 100

    if zona in zonas_medias:
        return 70

    if zona:
        return 50

    return DEFAULT_ZONE_SCORE


def _calculate_order_value_score(order: dict) -> int:
    """
    Estima valor operativo usando cantidad de productos.
    No usa precios ni inventario real.
    """

    productos = order.get("productos") or []

    if not productos:
        return DEFAULT_ORDER_VALUE_SCORE

    total_cantidad = 0

    for producto in productos:
        cantidad = producto.get("cantidad") or 0

        try:
            total_cantidad += float(cantidad)
        except (TypeError, ValueError):
            continue

    if total_cantidad >= 5:
        return 100

    if total_cantidad >= 2:
        return 70

    return 50
