# Simula una ruta falsa usando los pedidos guardados.
def generate_mock_route(orders: list[dict]) -> dict:
    return {
        "method": "MOCK_ROUTE",
        "fallback_used": True,
        "total_distance_km": 18.5,
        "total_time_min": 45,
        "stops": [
            {
                "order_id": order.get("id"),
                "cliente": order.get("cliente"),
                "zona": order.get("zona"),
                "priority": index + 1
            }
            for index, order in enumerate(orders)
        ]
    }
    
    #No calcula rutas reales todavía. 
    #Solo devuelve una estructura compatible con lo que después entregará OSRM/OpenRouteService.