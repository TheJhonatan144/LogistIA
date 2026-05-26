from src.llm_service import extract_order_from_text
import json

# Leer archivo de pruebas
with open("tests/pedidos_prueba.txt", "r", encoding="utf-8") as file:
    lines = file.readlines()

results = []

# Procesar cada pedido
for i, line in enumerate(lines):
    text = line.strip()

    if not text:
        continue

    print(f"\n--- Pedido {i+1} ---")
    print(f"Texto: {text}")

    result = extract_order_from_text(text)

    print("Resultado:")
    print(result)

    # Guardar resultado
    results.append({
        "input": text,
        "output": result
    })

# Guardar archivo JSON
with open("tests/resultados_llm.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)