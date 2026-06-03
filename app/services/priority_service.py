URGENCY_SCORE = {
    "alta": 50,
    "media": 30,
    "baja": 10,
}

CLIENT_TYPE_SCORE = {
    "vip": 20,
    "normal": 0,
}

ZONE_SCORE = {
    # Cerca / frecuente desde El Girón
    "el girón": 15,
    "centro histórico": 15,
    "la marín": 15,
    "cumbayá": 12,
    "tumbaco": 12,
    "puembo": 12,

    # Media
    "san rafael": 10,
    "sangolquí": 10,
    "conocoto": 10,

    # Lejana
    "calderón": 5,
    "carapungo": 5,
    "quitumbe": 5,
    "guamaní": 5,
}

VIP_CLIENTS = {
    "Fernanda",
}


def calculate_priority(order: dict) -> int:
    urgencia = (order.get("urgencia") or "media").lower()
    cliente = (order.get("cliente") or "").strip()
    tipo_cliente = _get_client_type(cliente)

    urgency_score = URGENCY_SCORE.get(urgencia, 30)
    client_score = CLIENT_TYPE_SCORE.get(tipo_cliente, 0)
    zone_score = _calculate_zone_score(order)
    order_value_score = _calculate_order_value_score(order)

    score = (
        urgency_score +
        client_score +
        zone_score +
        order_value_score
    )

    if order.get("hora_limite"):
        score += 5

    if order.get("errores"):
        score -= 25

    return max(0, min(100, round(score)))


def _get_client_type(cliente: str) -> str:
    return "vip" if cliente in VIP_CLIENTS else "normal"


def _calculate_zone_score(order: dict) -> int:
    zona = (order.get("zona") or "").lower().strip()
    return ZONE_SCORE.get(zona, 8 if zona else 0)


def _calculate_order_value_score(order: dict) -> int:
    productos = order.get("productos") or []

    total_cantidad = 0

    for producto in productos:
        cantidad = producto.get("cantidad") or 0

        try:
            total_cantidad += float(cantidad)
        except (TypeError, ValueError):
            continue

    if total_cantidad >= 5:
        return 15

    if total_cantidad >= 2:
        return 10

    if total_cantidad >= 1:
        return 5

    return 0