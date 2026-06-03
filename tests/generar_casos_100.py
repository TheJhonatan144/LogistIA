import json
import random
from pathlib import Path

OUTPUT_PATH = Path("tests/casos_evaluacion_100.json")

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

zonas = ["Cumbayá"]

plantillas_completas = [
    "El cliente {cliente} de {zona} necesita {cantidad1} teclados Logitech y {cantidad2} mouse Logitech urgente.",
    "{cliente} de {zona} necesita {cantidad1} teclados Logitech y {cantidad2} mouse Logitech.",
    "El cliente {cliente} en {zona} solicita {cantidad1} teclados Logitech y {cantidad2} mouse Logitech.",
    "Pedido para el cliente {cliente} de {zona}: {cantidad1} teclados Logitech y {cantidad2} mouse Logitech.",
    "El cliente {cliente}, sector {zona}, requiere {cantidad1} teclados Logitech y {cantidad2} mouse Logitech.",
    "Para el cliente {cliente} en {zona}, enviar {cantidad1} teclados Logitech y {cantidad2} mouse Logitech.",
]

plantillas_incompletas = [
    "Necesito {cantidad1} teclados Logitech y {cantidad2} mouse Logitech urgente.",
    "Enviar {cantidad1} teclados Logitech y {cantidad2} mouse Logitech urgente.",
    "Pedido urgente de {cantidad1} teclados Logitech y {cantidad2} mouse Logitech.",
    "Se necesitan {cantidad1} teclados Logitech y {cantidad2} mouse Logitech.",
]

casos = []

for i in range(1, 101):
    cliente = random.choice(clientes)
    zona = random.choice(zonas)
    cantidad1 = random.randint(1, 3)
    cantidad2 = random.randint(1, 3)

    # 85 casos completos, 15 incompletos
    if i <= 85:
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
print("Distribución: 85 pedidos completos + 15 pedidos incompletos")
