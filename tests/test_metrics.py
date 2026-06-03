import argparse
import json
import time
from pathlib import Path

import requests

API_URL = "http://127.0.0.1:8000/api/orders"


def calcular_tasa_exito(casos_exitosos: int, total_casos: int) -> float:
    if total_casos == 0:
        return 0.0
    return round((casos_exitosos / total_casos) * 100, 2)


def calcular_latencia_promedio(tiempos_segundos: list[float]) -> float:
    if not tiempos_segundos:
        return 0.0
    return round(sum(tiempos_segundos) / len(tiempos_segundos), 2)


def generar_resumen_metricas(resultados: list[dict]) -> dict:
    total_casos = len(resultados)
    casos_exitosos = sum(1 for r in resultados if r.get("exitoso") is True)
    tiempos = [r.get("tiempo_segundos", 0) for r in resultados]

    return {
        "total_casos": total_casos,
        "casos_exitosos": casos_exitosos,
        "casos_fallidos": total_casos - casos_exitosos,
        "tasa_exito_porcentaje": calcular_tasa_exito(casos_exitosos, total_casos),
        "latencia_promedio_segundos": calcular_latencia_promedio(tiempos),
    }


def contiene_error(respuesta: dict, texto_esperado: str) -> bool:
    errores = respuesta.get("errores")

    if errores is None:
        return False

    if isinstance(errores, str):
        errores = [errores]

    return any(texto_esperado.lower() in str(error).lower() for error in errores)


def evaluar_respuesta(caso: dict, respuesta: dict, status_code: int) -> tuple[bool, list[str]]:
    esperado = caso.get("esperado", {})
    observaciones = []

    if status_code != 200:
        observaciones.append(f"Status HTTP inesperado: {status_code}")
        return False, observaciones

    estado_esperado = esperado.get("estado_esperado")
    if estado_esperado and respuesta.get("estado") != estado_esperado:
        observaciones.append(
            f"Estado diferente. Esperado: {estado_esperado}, obtenido: {respuesta.get('estado')}"
        )

    if esperado.get("cliente_requerido") and not respuesta.get("cliente"):
        observaciones.append("No se extrajo cliente")

    if esperado.get("zona_requerida") and not respuesta.get("zona"):
        observaciones.append("No se extrajo zona")

    productos_minimos = esperado.get("productos_minimos")
    if productos_minimos is not None:
        productos = respuesta.get("productos") or []
        if len(productos) < productos_minimos:
            observaciones.append(
                f"Productos insuficientes. Esperado mínimo: {productos_minimos}, obtenido: {len(productos)}"
            )

    urgencia_esperada = esperado.get("urgencia_esperada")
    if urgencia_esperada and respuesta.get("urgencia") != urgencia_esperada:
        observaciones.append(
            f"Urgencia diferente. Esperado: {urgencia_esperada}, obtenido: {respuesta.get('urgencia')}"
        )

    error_esperado = esperado.get("error_esperado")
    if error_esperado and not contiene_error(respuesta, error_esperado):
        observaciones.append(
            f"No se detectó el error esperado: {error_esperado}")

    error_contiene = esperado.get("error_contiene")
    if error_contiene and not contiene_error(respuesta, error_contiene):
        observaciones.append(
            f"No se detectó un error que contenga: {error_contiene}")

    debe_detectar_error = esperado.get("debe_detectar_error")
    if debe_detectar_error and not respuesta.get("errores"):
        observaciones.append(
            "Se esperaba algún error de validación, pero errores vino vacío")

    return len(observaciones) == 0, observaciones


def leer_argumentos():
    parser = argparse.ArgumentParser(
        description="Evalúa el desempeño del agente LogistiAI con casos de prueba."
    )

    parser.add_argument(
        "--casos",
        default="tests/casos_evaluacion.json",
        help="Ruta del archivo JSON con los casos de evaluación.",
    )

    parser.add_argument(
        "--salida",
        default="tests/resultados_metricas.json",
        help="Ruta donde se guardarán los resultados de métricas.",
    )

    return parser.parse_args()


def main():
    args = leer_argumentos()

    casos_path = Path(args.casos)
    resultados_path = Path(args.salida)

    if not casos_path.exists():
        print(f"No existe el archivo de casos: {casos_path}")
        return

    casos = json.loads(casos_path.read_text(encoding="utf-8"))
    resultados = []

    print("Evaluando desempeño del agente LogistiAI")
    print("----------------------------------------")
    print(f"Archivo de casos: {casos_path}")
    print(f"Total de casos cargados: {len(casos)}")
    print()

    for caso in casos:
        payload = {"message": caso["entrada"]}
        inicio = time.time()

        try:
            response = requests.post(API_URL, json=payload, timeout=90)
            tiempo = round(time.time() - inicio, 2)

            try:
                respuesta_json = response.json()
            except Exception:
                respuesta_json = {"raw_response": response.text}

            exitoso, observaciones = evaluar_respuesta(
                caso=caso,
                respuesta=respuesta_json,
                status_code=response.status_code,
            )

            resultado = {
                "id": caso["id"],
                "tipo": caso["tipo"],
                "entrada": caso["entrada"],
                "status_code": response.status_code,
                "tiempo_segundos": tiempo,
                "exitoso": exitoso,
                "observaciones": observaciones,
                "respuesta": respuesta_json,
            }

        except Exception as e:
            tiempo = round(time.time() - inicio, 2)
            resultado = {
                "id": caso["id"],
                "tipo": caso["tipo"],
                "entrada": caso["entrada"],
                "status_code": None,
                "tiempo_segundos": tiempo,
                "exitoso": False,
                "observaciones": [str(e)],
                "respuesta": None,
            }

        resultados.append(resultado)

        estado = "OK" if resultado["exitoso"] else "FALLO"
        print(
            f"Caso {caso['id']} - {caso['tipo']}: "
            f"{estado} ({resultado['tiempo_segundos']}s)"
        )

        for obs in resultado["observaciones"]:
            print(f"  - {obs}")

    resumen = generar_resumen_metricas(resultados)

    salida = {
        "archivo_casos": str(casos_path),
        "resumen": resumen,
        "resultados": resultados,
    }

    resultados_path.parent.mkdir(parents=True, exist_ok=True)
    resultados_path.write_text(
        json.dumps(salida, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print()
    print("Resumen")
    print("-------")
    print(json.dumps(resumen, ensure_ascii=False, indent=2))
    print()
    print(f"Resultados guardados en: {resultados_path}")


if __name__ == "__main__":
    main()
