# revisa si el pedido tiene datos mínimos

def validate_order(order: dict) -> tuple[bool, list[str]]:
    errors = []

    if not order.get("cliente"):
        errors.append("Falta cliente")

    if not order.get("zona"):
        errors.append("Falta zona")

    productos = order.get("productos", [])

    if not productos:
        errors.append("Faltan productos")

    for product in productos:
        if not product.get("nombre"):
            errors.append("Falta nombre del producto")

        if not product.get("cantidad"):
            errors.append("Falta cantidad del producto")

        if not product.get("unidad"):
            errors.append("Falta unidad del producto")

    return len(errors) == 0, errors