# Servicio de Ruteo OSM — LogistiAI

## Objetivo

Este módulo implementa el servicio de ruteo para LogistiAI. Permite calcular rutas desde una zona de origen hacia una o varias zonas destino usando servicios externos de mapas y, si estos fallan, una matriz local como respaldo.

La bodega inicial del sistema es:

- El Girón

## Archivo principal

`app/services/routing_service.py`

## Funciones implementadas

- `get_route(origin_zone: str, destination_zones: list[str]) -> dict`
- `get_route_osrm(origin_coords: dict, destination_coords: dict) -> dict`
- `get_route_openrouteservice(origin_coords: dict, destination_coords: dict) -> dict`
- `get_route_local_matrix(origin_zone: str, destination_zone: str) -> dict`
- `get_zone_coordinates(zone_name: str) -> dict | None`

## Flujo de ruteo

El servicio intenta calcular la ruta en el siguiente orden:

1. OSRM
2. OpenRouteService
3. Matriz local

Si OSRM responde correctamente, se usa esa ruta.

Si OSRM falla, se intenta usar OpenRouteService.

Si OpenRouteService falla o no existe una API key configurada, se usa la matriz local como fallback obligatorio.

## Zonas soportadas inicialmente

- El Girón
- La Magdalena
- El Condado
- La Carolina
- Centro Histórico
- Cumbayá
- Tumbaco
- Calderón
- Carapungo
- Valle de los Chillos
- Sur
- Norte
- Centro

## Formato de respuesta

El servicio devuelve un diccionario con el siguiente formato:

```json
{
  "method": "OSRM",
  "fallback_used": false,
  "total_distance_km": 21.42,
  "total_time_min": 28,
  "stops": [
    {
      "zona": "La Magdalena",
      "distance_km": 9.71,
      "time_min": 13
    },
    {
      "zona": "La Carolina",
      "distance_km": 11.71,
      "time_min": 15
    }
  ]
}
```

## Ejemplo de prueba con OSRM

Prueba ejecutada desde la raíz del proyecto:

```python
from app.services.routing_service import get_route

resultado = get_route("El Girón", ["La Magdalena", "La Carolina"])
print(resultado)
```

Resultado obtenido:

```python
{
  'method': 'OSRM',
  'fallback_used': False,
  'total_distance_km': 21.42,
  'total_time_min': 28,
  'stops': [
    {
      'zona': 'La Magdalena',
      'distance_km': 9.71,
      'time_min': 13
    },
    {
      'zona': 'La Carolina',
      'distance_km': 11.71,
      'time_min': 15
    }
  ]
}
```

## Ejemplo de fallback local

Prueba ejecutada con una zona no registrada:

```python
from app.services.routing_service import get_route

resultado = get_route("El Girón", ["Zona Inventada"])
print(resultado)
```

Resultado obtenido:

```python
{
  'method': 'LOCAL_MATRIX',
  'fallback_used': True,
  'total_distance_km': 0.0,
  'total_time_min': 0,
  'stops': [
    {
      'zona': 'Zona Inventada',
      'distance_km': 0.0,
      'time_min': 0
    }
  ]
}
```

## Variables de entorno relacionadas

```env
ORS_API_KEY=
ROUTING_PROVIDER=AUTO
DEFAULT_WAREHOUSE_ZONE=El Girón
```

`ORS_API_KEY` se usa únicamente si se desea consultar OpenRouteService.

Si no existe esta variable, el sistema puede seguir funcionando con OSRM o con la matriz local.

## Restricciones del módulo

Este servicio:

- No calcula prioridad.
- No modifica pedidos.
- No guarda datos directamente en SQLite.
- No usa Google Maps.
- No usa geocodificación libre en vivo.
- No contiene tokens ni credenciales reales.
- No cambia el formato de respuesta esperado por planificación.
