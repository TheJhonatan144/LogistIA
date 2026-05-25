# Integrante resplaza este MOCK
# Simulacion temporal del comportamiento de la IA

def extract_order_from_text(text: str) -> dict:
    return {
        "cliente": "Carmen",
        "telefono": None,
        "zona": "La Magdalena",
        "direccion": None,
        "productos": [
            {
                "nombre": "arroz",
                "cantidad": 2,
                "unidad": "quintales"
            }
        ],
        "urgencia": "alta",
        "hora_limite": None,
        "observaciones": text,
        "estado": "recibido"
    }