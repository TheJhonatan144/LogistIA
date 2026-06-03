import json
import random
from pathlib import Path

OUTPUT_PATH = Path("tests/casos_evaluacion_1000.json")

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

productos = [
    ("teclados Logitech", "teclado Logitech"),
    ("mouse Logitech", "mouse Logitech"),
]

plantillas_completas = [
    "El cliente {cliente} de {zona} necesita {cantidad1} {producto1} y {cantidad2} {producto2} urgente.",
    "{cliente} en {zona} solicita {cantidad1} {producto1} y {cantidad2} {producto2}. Es urgente.",
    "Pedido para {cliente} de {zona}: {cantidad1} {producto1} y {cantidad2} {producto2}.",
    "El cliente {cliente}, sector {zona}, requiere {cantidad1} {producto1} y {cantidad2} {producto2}.",
]

plantillas_incompletas = [
    "Necesito {cantidad1} {producto1} y {cantidad2} {producto2} urgente.",
    "Enviar {cantidad1} {producto1} a un cliente urgente.",
    "Pedido urgente de {cantidad1} {producto1} y {cantidad2} {producto2}.",
]

casos = []

for i in range(1, 1001):
    cliente = random.choice(clientes)
    zona = random.choice(zonas)

    producto1_texto, _ = productos[0]
    producto2_texto, _ = productos[1]

    cantidad1 = random.randint(1, 3)
    cantidad2 = random.randint(1, 3)

    # 80% pedidos completos, 20% incompletos
    if i <= 800:
        plantilla = random.choice(plantillas_completas)
        entrada = plantilla.format(
            cliente=cliente,
            zona=zona,
            cantidad1=cantidad1,
            producto1=producto1_texto,
            cantidad2=cantidad2,
            producto2=producto2_texto,
        )

        caso = {
            "id": i,
            "tipo": "pedido_completo",
            "descripcion": "Pedido completo generado automáticamente.",
            "entrada": entrada,
            "esperado": {
                "debe_ser_exitoso": True,
                "cliente_requerido": True,
                "zona_requerida": True,
                "productos_minimos": 1
            }
        }

    else:
        plantilla = random.choice(plantillas_incompletas)
        entrada = plantilla.format(
            cantidad1=cantidad1,
            producto1=producto1_texto,
            cantidad2=cantidad2,
            producto2=producto2_texto,
        )

        caso = {
            "id": i,
            "tipo": "pedido_incompleto",
            "descripcion": "Pedido incompleto generado automáticamente.",
            "entrada": entrada,
            "esperado": {
                "debe_ser_exitoso": True,
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
