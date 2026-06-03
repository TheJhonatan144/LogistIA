from statistics import mean


def calcular_tasa_exito(casos_exitosos: int, total_casos: int) -> float:
    """
    Calcula la tasa de éxito como porcentaje.
    """
    if total_casos == 0:
        return 0.0

    return round((casos_exitosos / total_casos) * 100, 2)


def calcular_latencia_promedio(tiempos_segundos: list[float]) -> float:
    """
    Calcula el tiempo promedio de respuesta en segundos.
    """
    if not tiempos_segundos:
        return 0.0

    return round(mean(tiempos_segundos), 2)


def generar_resumen_metricas(resultados: list[dict]) -> dict:
    """
    Genera un resumen general a partir de los resultados de prueba.
    Cada resultado debe incluir:
    - exitoso: bool
    - tiempo_segundos: float
    """
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
