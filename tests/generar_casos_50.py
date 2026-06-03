import json
import random
from pathlib import Path

OUTPUT_PATH = Path("tests/casos_evaluacion_50.json")

clientes = [
    "Juan Pérez",
    "Ana Torres",
    "Carlos Méndez",
    "María López",
    "Pedro Sánchez",
    "Lucía Gómez",
    "Diego Morales",
    "Sofía Ramírez",
    "Andrés Castillo",
    "Valeria Ruiz",
]

zonas = [
    "Cumbayá",
]

plantillas_completas = [
    "El cliente {cliente} de {zona} necesita {cantidad1} teclados Logitech y {cantidad2} mouse Logitech urgente.",
    "{cliente} en {zona} solicita {cantidad1} teclados Logitech y {cantidad2} mouse Logitech. Es urgente.",
    "Pedido para {cliente} de {zona}: {cantidad1} teclados Logitech y {cantidad2} mouse Logitech.",
    "El cliente {cliente}, sector {zona}, requiere {cantidad1} teclados Logitech y {cantidad2} mouse Logitech.",
    "Para {cliente} en {zona}, enviar {cantidad1} teclados Logitech y {cantidad2} mouse Logitech.",
]

plantillas_incompletas = [
    "Necesito {cantidad1} teclados Logitech y {cantidad2} mouse Logitech urgente.",
    "Enviar {cantidad1} teclados Logitech y {cantidad2} mouse Logitech urgente.",
    "Pedido urgente de {cantidad1} teclados Logitech y {cantidad2} mouse Logitech.",
    "Se necesitan {cantidad1} teclados Logitech y {cantidad2} mouse Logitech.",
]

casos = []

for i in range(1, 51):
    cliente = random.choice(clientes)
    zona = random.choice(zonas)
    cantidad1 = random.randint(1, 3)
    cantidad2 = random.randint(1, 3)

    # 40 casos completos, 10 incompletos
    if i <= 40:
        plantilla = random.choice(plantillas_completas)
        entrada = plantilla.format(
            cliente=cliente,
            zona=zona,
            cantidad1=cantidad1,
            cantidad2=cantidad2,
        )

        caso = {
            "id": i,
            "tipo": "pedido_completo",
            "descripcion": "Pedido completo generado automáticamente.",
            "entrada": entrada,
            "esperado": {
                "cliente_requerido": True,
                "zona_requerida": True,
                "productos_minimos": 1
            }
        }

    else:
        plantilla = random.choice(plantillas_incompletas)
        entrada = plantilla.format(
            cantidad1=cantidad1,
            cantidad2=cantidad2,
        )

        caso = {
            "id": i,
            "tipo": "pedido_incompleto",
            "descripcion": "Pedido incompleto generado automáticamente.",
            "entrada": entrada,
            "esperado": {
                "debe_detectar_error": True
            }
        }

    casos.append(caso)

OUTPUT_PATH.write_text(
    json.dumps(casos, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

print(f"Archivo generado: {OUTPUT_PATH}")
print(f"Total de casos: {len(casos)}")
print("Distribución: 40 pedidos completos + 10 pedidos incompletos")
