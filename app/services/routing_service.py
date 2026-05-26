import math
import os
from typing import Optional

import requests


ZONE_COORDINATES = {
    "El Girón": {"lat": -0.1951, "lon": -78.4893},
    "La Magdalena": {"lat": -0.2500, "lon": -78.5300},
    "El Condado": {"lat": -0.1030, "lon": -78.4900},
    "La Carolina": {"lat": -0.1830, "lon": -78.4840},
    "Centro Histórico": {"lat": -0.2202, "lon": -78.5127},
    "Cumbayá": {"lat": -0.2000, "lon": -78.4300},
    "Tumbaco": {"lat": -0.2167, "lon": -78.4000},
    "Calderón": {"lat": -0.0950, "lon": -78.4300},
    "Carapungo": {"lat": -0.0900, "lon": -78.4550},
    "Valle de los Chillos": {"lat": -0.3000, "lon": -78.4500},
    "Sur": {"lat": -0.2800, "lon": -78.5400},
    "Norte": {"lat": -0.1200, "lon": -78.4800},
    "Centro": {"lat": -0.2100, "lon": -78.5000},
}


LOCAL_ROUTE_MATRIX = {
    ("El Girón", "La Magdalena"): {"distance_km": 9.0, "time_min": 25},
    ("El Girón", "El Condado"): {"distance_km": 13.0, "time_min": 35},
    ("El Girón", "La Carolina"): {"distance_km": 3.5, "time_min": 12},
    ("El Girón", "Centro Histórico"): {"distance_km": 5.0, "time_min": 18},
    ("El Girón", "Cumbayá"): {"distance_km": 12.0, "time_min": 30},
    ("El Girón", "Tumbaco"): {"distance_km": 18.0, "time_min": 40},
    ("El Girón", "Calderón"): {"distance_km": 16.0, "time_min": 38},
    ("El Girón", "Carapungo"): {"distance_km": 18.0, "time_min": 42},
    ("El Girón", "Valle de los Chillos"): {"distance_km": 20.0, "time_min": 45},
    ("El Girón", "Sur"): {"distance_km": 12.0, "time_min": 35},
    ("El Girón", "Norte"): {"distance_km": 8.0, "time_min": 25},
    ("El Girón", "Centro"): {"distance_km": 5.0, "time_min": 18},
}


def get_zone_coordinates(zone_name: str) -> Optional[dict]:
    if not zone_name:
        return None

    return ZONE_COORDINATES.get(zone_name.strip())


def get_route_osrm(origin_coords: dict, destination_coords: dict) -> dict:
    origin = f'{origin_coords["lon"]},{origin_coords["lat"]}'
    destination = f'{destination_coords["lon"]},{destination_coords["lat"]}'

    url = (
        "https://router.project-osrm.org/route/v1/driving/"
        f"{origin};{destination}"
    )

    params = {
        "overview": "false",
        "alternatives": "false",
        "steps": "false",
    }

    response = requests.get(url, params=params, timeout=8)
    response.raise_for_status()

    data = response.json()

    if data.get("code") != "Ok" or not data.get("routes"):
        raise ValueError("OSRM no devolvió una ruta válida")

    route = data["routes"][0]

    return {
        "distance_km": round(route["distance"] / 1000, 2),
        "time_min": round(route["duration"] / 60),
    }


def get_route_openrouteservice(origin_coords: dict, destination_coords: dict) -> dict:
    api_key = os.getenv("ORS_API_KEY")

    if not api_key:
        raise ValueError("ORS_API_KEY no configurada")

    url = "https://api.openrouteservice.org/v2/directions/driving-car"

    headers = {
        "Authorization": api_key,
        "Content-Type": "application/json",
    }

    payload = {
        "coordinates": [
            [origin_coords["lon"], origin_coords["lat"]],
            [destination_coords["lon"], destination_coords["lat"]],
        ]
    }

    response = requests.post(url, json=payload, headers=headers, timeout=8)
    response.raise_for_status()

    data = response.json()

    routes = data.get("routes")
    if not routes:
        raise ValueError("OpenRouteService no devolvió una ruta válida")

    summary = routes[0]["summary"]

    return {
        "distance_km": round(summary["distance"] / 1000, 2),
        "time_min": round(summary["duration"] / 60),
    }


def get_route_local_matrix(origin_zone: str, destination_zone: str) -> dict:
    direct_key = (origin_zone, destination_zone)
    reverse_key = (destination_zone, origin_zone)

    if direct_key in LOCAL_ROUTE_MATRIX:
        return LOCAL_ROUTE_MATRIX[direct_key]

    if reverse_key in LOCAL_ROUTE_MATRIX:
        return LOCAL_ROUTE_MATRIX[reverse_key]

    origin_coords = get_zone_coordinates(origin_zone)
    destination_coords = get_zone_coordinates(destination_zone)

    if not origin_coords or not destination_coords:
        return {
            "distance_km": 0.0,
            "time_min": 0,
        }

    distance_km = _estimate_distance_km(origin_coords, destination_coords)

    return {
        "distance_km": distance_km,
        "time_min": round(distance_km * 3),
    }


def get_route(origin_zone: str, destination_zones: list[str]) -> dict:
    if not origin_zone:
        origin_zone = os.getenv("DEFAULT_WAREHOUSE_ZONE", "El Girón")

    if not destination_zones:
        return {
            "method": "LOCAL_MATRIX",
            "fallback_used": True,
            "total_distance_km": 0.0,
            "total_time_min": 0,
            "stops": [],
        }

    current_zone = origin_zone
    total_distance_km = 0.0
    total_time_min = 0
    stops = []

    methods_used = []
    fallback_used = False

    for destination_zone in destination_zones:
        origin_coords = get_zone_coordinates(current_zone)
        destination_coords = get_zone_coordinates(destination_zone)

        try:
            if not origin_coords or not destination_coords:
                raise ValueError("Zona sin coordenadas configuradas")

            route_data = get_route_osrm(origin_coords, destination_coords)
            method = "OSRM"

        except Exception:
            try:
                if not origin_coords or not destination_coords:
                    raise ValueError("Zona sin coordenadas configuradas")

                route_data = get_route_openrouteservice(origin_coords, destination_coords)
                method = "OPENROUTESERVICE"

            except Exception:
                route_data = get_route_local_matrix(current_zone, destination_zone)
                method = "LOCAL_MATRIX"
                fallback_used = True

        methods_used.append(method)

        distance_km = route_data["distance_km"]
        time_min = route_data["time_min"]

        total_distance_km += distance_km
        total_time_min += time_min

        stops.append(
            {
                "zona": destination_zone,
                "distance_km": distance_km,
                "time_min": time_min,
            }
        )

        current_zone = destination_zone

    return {
        "method": _resolve_method(methods_used),
        "fallback_used": fallback_used,
        "total_distance_km": round(total_distance_km, 2),
        "total_time_min": total_time_min,
        "stops": stops,
    }


def _resolve_method(methods_used: list[str]) -> str:
    unique_methods = set(methods_used)

    if len(unique_methods) == 1:
        return methods_used[0]

    if "LOCAL_MATRIX" in unique_methods:
        return "MIXED_WITH_LOCAL_MATRIX"

    return "MIXED"


def _estimate_distance_km(origin_coords: dict, destination_coords: dict) -> float:
    lat1 = math.radians(origin_coords["lat"])
    lon1 = math.radians(origin_coords["lon"])
    lat2 = math.radians(destination_coords["lat"])
    lon2 = math.radians(destination_coords["lon"])

    earth_radius_km = 6371

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    haversine = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )

    straight_distance = 2 * earth_radius_km * math.asin(math.sqrt(haversine))

    return round(straight_distance * 1.35, 2)