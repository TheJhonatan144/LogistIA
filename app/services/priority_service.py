# Convierte urgencia en puntaje.

URGENCY_SCORE = {
    "alta": 100,
    "media": 60,
    "baja": 30
}


def calculate_priority(order: dict) -> int:
    urgency = order.get("urgencia", "media").lower()

    base_score = URGENCY_SCORE.get(urgency, 60)

    products = order.get("productos", [])
    product_bonus = min(len(products) * 5, 20)

    final_score = base_score + product_bonus

    return min(final_score, 100)