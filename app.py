from __future__ import annotations

import os
from typing import Any

import requests
import streamlit as st


API_BASE_URL_DEFAULT = os.getenv("LOGISTIAI_API_URL", "http://127.0.0.1:8000")


st.set_page_config(
    page_title="LogistiAI | Panel de despacho",
    page_icon="🚚",
    layout="wide",
)


# ============================================================
# Estado inicial
# ============================================================

def init_state() -> None:
    st.session_state.setdefault("api_base_url", API_BASE_URL_DEFAULT)
    st.session_state.setdefault("last_order_response", None)
    st.session_state.setdefault("last_dispatch_plan", None)


# ============================================================
# Cliente HTTP hacia el backend
# ============================================================

def api_request(
    method: str,
    endpoint: str,
    payload: dict[str, Any] | None = None,
    timeout: int = 15,
) -> tuple[Any | None, str | None]:
    """
    Ejecuta una petición HTTP contra el backend.

    Importante:
    - Streamlit NO interpreta pedidos.
    - Streamlit NO calcula score.
    - Streamlit NO calcula rutas.
    - Streamlit NO guarda directamente en SQLite.
    - Streamlit solo consume endpoints del backend.
    """
    base_url = st.session_state.get("api_base_url", API_BASE_URL_DEFAULT).rstrip("/")
    url = f"{base_url}{endpoint}"

    try:
        response = requests.request(
            method=method.upper(),
            url=url,
            json=payload if method.upper() != "GET" else None,
            timeout=timeout,
        )
        response.raise_for_status()

        if not response.content:
            return {}, None

        try:
            return response.json(), None
        except ValueError:
            return {"respuesta": response.text}, None

    except requests.exceptions.ConnectionError:
        return None, (
            "No se pudo conectar con el backend. "
            "Verifica que el servidor FastAPI esté encendido."
        )
    except requests.exceptions.Timeout:
        return None, "La petición tardó demasiado. Intenta nuevamente."
    except requests.exceptions.HTTPError as exc:
        status_code = exc.response.status_code if exc.response else "?"
        detail: Any = ""

        if exc.response is not None:
            try:
                detail = exc.response.json()
            except ValueError:
                detail = exc.response.text

        return None, f"Error HTTP {status_code}: {detail}"
    except requests.exceptions.RequestException as exc:
        return None, f"Error al consumir el backend: {exc}"


# ============================================================
# Utilidades para leer respuestas variables del backend
# ============================================================

def get_path(data: Any, path: str, default: Any = None) -> Any:
    current = data

    for part in path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return default

    return current


def pick(data: Any, *paths: str, default: Any = "—") -> Any:
    for path in paths:
        value = get_path(data, path)

        if value not in (None, "", [], {}):
            return value

    return default


def extract_orders(payload: Any) -> list[dict[str, Any]]:
    """
    Normaliza posibles respuestas del endpoint GET /api/orders.

    Soporta respuestas como:
    - [{"id": 1, ...}]
    - {"orders": [...]}
    - {"pedidos": [...]}
    - {"data": [...]}
    """
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]

    if isinstance(payload, dict):
        for key in ("orders", "pedidos", "data", "items", "results"):
            value = payload.get(key)

            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]

    return []


def order_to_row(order: dict[str, Any], index: int) -> dict[str, Any]:
    return {
        "id": pick(order, "id", "order_id", "pedido_id", default=index),
        "cliente": pick(
            order,
            "cliente",
            "cliente_nombre",
            "customer",
            "customer_name",
            "client.name",
            default="No identificado",
        ),
        "zona": pick(
            order,
            "zona",
            "sector",
            "zone",
            "delivery_zone",
            default="No identificada",
        ),
        "urgencia": pick(
            order,
            "urgencia",
            "urgency",
            "prioridad",
            "priority",
            default="—",
        ),
        "estado": pick(
            order,
            "estado",
            "status",
            "order_status",
            default="—",
        ),
        "score_prioridad": pick(
            order,
            "score_prioridad",
            "priority_score",
            "score",
            "prioridad_score",
            default="—",
        ),
    }


def orders_to_rows(orders: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [order_to_row(order, index) for index, order in enumerate(orders, start=1)]


def count_statuses(orders: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}

    for order in orders:
        status = str(
            pick(order, "estado", "status", "order_status", default="sin_estado")
        ).lower()

        counts[status] = counts.get(status, 0) + 1

    return counts


def count_by_fragments(counts: dict[str, int], fragments: list[str]) -> int:
    total = 0

    for status, amount in counts.items():
        if any(fragment in status for fragment in fragments):
            total += amount

    return total


def extract_stops_from_zones(zones: dict[str, Any]) -> list[dict[str, Any]]:
    stops: list[dict[str, Any]] = []
    sequence = 1

    for zone_name, zone_orders in zones.items():
        if not isinstance(zone_orders, list):
            continue

        for order in zone_orders:
            if isinstance(order, dict):
                stop = {
                    "orden": sequence,
                    "cliente": pick(order, "cliente", "customer", default="—"),
                    "zona": pick(order, "zona", "zone", default=zone_name),
                    "direccion": pick(order, "direccion", "address", default="—"),
                    "estado": pick(order, "estado", "status", default="—"),
                    "score_prioridad": pick(
                        order,
                        "score_prioridad",
                        "priority_score",
                        "score",
                        default="—",
                    ),
                }
            else:
                stop = {
                    "orden": sequence,
                    "cliente": str(order),
                    "zona": zone_name,
                    "direccion": "—",
                    "estado": "—",
                    "score_prioridad": "—",
                }

            stops.append(stop)
            sequence += 1

    return stops


def extract_stops(plan: Any) -> list[Any]:
    """
    Extrae paradas del plan sin calcular rutas.

    Solo adapta la respuesta del backend para mostrarla en tabla.
    """
    if not isinstance(plan, dict):
        return []

    direct_paths = (
        "stops",
        "paradas",
        "ruta",
        "orden_entrega",
        "delivery_order",
        "route.stops",
        "route.paradas",
        "routing.stops",
        "routing.paradas",
        "plan.stops",
        "plan.paradas",
    )

    for path in direct_paths:
        value = get_path(plan, path)

        if isinstance(value, list):
            return value

    zones = plan.get("zones")

    if isinstance(zones, dict):
        return extract_stops_from_zones(zones)

    return []


def stop_to_row(stop: Any, index: int) -> dict[str, Any]:
    if not isinstance(stop, dict):
        return {
            "orden": index,
            "cliente": str(stop),
            "zona": "—",
            "direccion": "—",
            "tiempo_estimado": "—",
            "distancia_estimada": "—",
        }

    return {
        "orden": pick(stop, "orden", "order", "sequence", default=index),
        "cliente": pick(
            stop,
            "cliente",
            "customer",
            "customer_name",
            "order.cliente",
            default="—",
        ),
        "zona": pick(
            stop,
            "zona",
            "zone",
            "sector",
            "order.zona",
            default="—",
        ),
        "direccion": pick(
            stop,
            "direccion",
            "address",
            "delivery_address",
            "order.direccion",
            default="—",
        ),
        "tiempo_estimado": pick(
            stop,
            "tiempo_estimado",
            "estimated_time",
            "time_min",
            "duration",
            default="—",
        ),
        "distancia_estimada": pick(
            stop,
            "distancia_estimada",
            "distance_km",
            "distance",
            default="—",
        ),
    }


def stops_to_rows(stops: list[Any]) -> list[dict[str, Any]]:
    return [stop_to_row(stop, index) for index, stop in enumerate(stops, start=1)]


# ============================================================
# Sidebar
# ============================================================

def render_sidebar() -> None:
    with st.sidebar:
        st.title("🚚 LogistiAI")
        st.caption("Panel operativo de despacho")

        st.divider()

        st.subheader("Estado del sistema")

        if st.button("Verificar conexión", use_container_width=True):
            data, error = api_request("GET", "/health", timeout=5)

            if error:
                st.error(error)
            else:
                st.success("Backend disponible")
                with st.expander("Ver respuesta técnica"):
                    st.json(data)

        with st.expander("Configuración de conexión"):
            st.text_input(
                "URL base del backend",
                key="api_base_url",
                help="URL local o remota del backend de LogistiAI.",
            )

        st.divider()
        st.caption(
            "Este panel permite registrar pedidos, revisar estados "
            "y generar planes de despacho desde el backend de LogistiAI."
        )


# ============================================================
# Pantallas del cliente
# ============================================================

def render_summary(orders: list[dict[str, Any]], orders_error: str | None) -> None:
    st.header("Resumen general")

    if orders_error:
        st.warning(orders_error)

    counts = count_statuses(orders)

    total_orders = len(orders)
    received = count_by_fragments(counts, ["recibido", "received"])
    pending = count_by_fragments(counts, ["pendiente", "pending"])
    ready = count_by_fragments(counts, ["listo", "ready"])
    planned = count_by_fragments(counts, ["planificado", "planned"])

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total pedidos", total_orders)
    col2.metric("Recibidos", received)
    col3.metric("Pendientes", pending)
    col4.metric("Listos despacho", ready)
    col5.metric("Planificados", planned)

    st.subheader("Pedidos por estado")

    if counts:
        rows = [
            {"estado": status, "cantidad": amount}
            for status, amount in sorted(counts.items())
        ]
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.info("Todavía no hay pedidos registrados.")


def render_order_registration() -> None:
    st.header("Registrar pedido")

    st.write(
        "Ingresa el pedido recibido por la empresa. "
        "El backend se encargará de interpretarlo, validarlo y registrarlo."
    )

    message = st.text_area(
        "Pedido en lenguaje natural",
        placeholder=(
            "Ejemplo: La señora Carmen de La Magdalena necesita "
            "2 quintales de arroz y una caja de aceite. Es urgente."
        ),
        height=150,
    )

    if st.button("Registrar pedido", type="primary", use_container_width=True):
        if not message.strip():
            st.warning("Escribe un pedido antes de registrarlo.")
            return

        payload = {"message": message.strip()}
        data, error = api_request("POST", "/api/orders", payload=payload, timeout=30)

        if error:
            st.error(error)
            return

        st.session_state["last_order_response"] = data
        st.success("Pedido enviado correctamente al backend.")

    if st.session_state.get("last_order_response") is not None:
        st.subheader("Resultado del registro")
        st.json(st.session_state["last_order_response"])


def render_orders_list(orders: list[dict[str, Any]], orders_error: str | None) -> None:
    st.header("Lista de pedidos")

    col1, col2 = st.columns([3, 1])

    with col1:
        st.write("Consulta los pedidos registrados y su información logística.")

    with col2:
        if st.button("Actualizar", use_container_width=True):
            st.rerun()

    if orders_error:
        st.error(orders_error)
        return

    if not orders:
        st.info("No hay pedidos para mostrar.")
        return

    rows = orders_to_rows(orders)
    st.dataframe(rows, use_container_width=True, hide_index=True)

    st.subheader("Detalle del pedido")

    selected_index = st.selectbox(
        "Selecciona un pedido",
        options=list(range(len(orders))),
        format_func=lambda index: (
            f"Pedido {rows[index]['id']} - {rows[index]['cliente']}"
        ),
    )

    st.json(orders[selected_index])


def render_status_view(orders: list[dict[str, Any]]) -> None:
    st.header("Estado de pedidos")

    st.write(
        "Revisa el estado operativo de los pedidos registrados en el sistema."
    )

    data, error = api_request("GET", "/api/status", timeout=10)

    if error:
        st.warning(
            "No se pudo consultar el estado general del backend. "
            "Se muestran estados derivados del listado de pedidos."
        )

        counts = count_statuses(orders)

        if not counts:
            st.info("No hay información de estados disponible.")
            return

        rows = [
            {"estado": status, "cantidad": amount}
            for status, amount in sorted(counts.items())
        ]
        st.dataframe(rows, use_container_width=True, hide_index=True)
        return

    st.subheader("Estado general del sistema")
    st.json(data)


def render_plan_summary(plan: Any) -> None:
    if not isinstance(plan, dict):
        st.json(plan)
        return

    total = pick(
        plan,
        "total_orders",
        "total_pedidos",
        "pedidos_total",
        "total",
        "summary.total_orders",
        default="No especificado",
    )

    route_method = pick(
        plan,
        "routing_method",
        "route_method",
        "metodo_ruteo",
        "metodo",
        "routing.method",
        "route.method",
        default="No especificado",
    )

    distance = pick(
        plan,
        "distance_km",
        "distancia_km",
        "distancia_estimada",
        "distancia_estimada_km",
        "route.distance_km",
        "route.total_distance_km",
        "routing.distance_km",
        default="No especificada",
    )

    estimated_time = pick(
        plan,
        "time_min",
        "tiempo_min",
        "estimated_time_min",
        "tiempo_estimado",
        "tiempo_estimado_min",
        "route.time_min",
        "route.total_time_min",
        "routing.time_min",
        default="No especificado",
    )

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Pedidos incluidos", total)
    col2.metric("Método de ruta", route_method)
    col3.metric("Distancia estimada", distance)
    col4.metric("Tiempo estimado", estimated_time)

    stops = extract_stops(plan)

    st.subheader("Paradas sugeridas")

    if stops:
        st.dataframe(stops_to_rows(stops), use_container_width=True, hide_index=True)
    else:
        st.info("El backend no devolvió paradas para este plan.")

    explanation = pick(
        plan,
        "explicacion",
        "explanation",
        "detalle",
        "summary.explanation",
        default=None,
    )

    if explanation:
        st.subheader("Explicación del plan")
        st.info(str(explanation))

    with st.expander("Ver respuesta completa del backend"):
        st.json(plan)


def render_dispatch_plan() -> None:
    st.header("Plan de despacho")

    st.write(
        "Genera un plan de despacho con los pedidos listos para entrega. "
        "La priorización y el ruteo son calculados por el backend."
    )

    if st.button("Generar plan de despacho", type="primary", use_container_width=True):
        data, error = api_request("POST", "/api/dispatch/plan", payload={}, timeout=30)

        if error:
            st.error(error)
            return

        st.session_state["last_dispatch_plan"] = data
        st.success("Plan de despacho generado correctamente.")

    if st.session_state.get("last_dispatch_plan") is None:
        st.info("Presiona el botón para solicitar el plan de despacho.")
    else:
        render_plan_summary(st.session_state["last_dispatch_plan"])


def render_route_view() -> None:
    st.header("Ruta sugerida")

    plan = st.session_state.get("last_dispatch_plan")

    if plan is None:
        st.info("Primero genera un plan de despacho.")
        return

    if not isinstance(plan, dict):
        st.json(plan)
        return

    route_method = pick(
        plan,
        "routing_method",
        "route_method",
        "metodo_ruteo",
        "metodo",
        "routing.method",
        "route.method",
        default="No especificado",
    )

    distance = pick(
        plan,
        "distance_km",
        "distancia_km",
        "distancia_estimada",
        "route.distance_km",
        "route.total_distance_km",
        "routing.distance_km",
        default="No especificada",
    )

    estimated_time = pick(
        plan,
        "time_min",
        "tiempo_min",
        "estimated_time_min",
        "tiempo_estimado",
        "route.time_min",
        "route.total_time_min",
        "routing.time_min",
        default="No especificado",
    )

    col1, col2, col3 = st.columns(3)
    col1.metric("Método de ruteo", route_method)
    col2.metric("Distancia estimada", distance)
    col3.metric("Tiempo estimado", estimated_time)

    stops = extract_stops(plan)

    st.subheader("Orden sugerido de entrega")

    if stops:
        st.dataframe(stops_to_rows(stops), use_container_width=True, hide_index=True)
    else:
        st.warning("No se encontraron paradas en el plan actual.")

    with st.expander("Ver datos completos de la ruta"):
        st.json(plan)


# ============================================================
# Aplicación principal
# ============================================================

def main() -> None:
    init_state()
    render_sidebar()

    st.title("Panel de despacho LogistiAI")
    st.caption(
        "Gestión visual de pedidos, estados, planificación y ruta sugerida."
    )

    orders_payload, orders_error = api_request("GET", "/api/orders", timeout=10)
    orders = extract_orders(orders_payload)

    tabs = st.tabs(
        [
            "Resumen general",
            "Registrar pedido",
            "Lista de pedidos",
            "Estado de pedidos",
            "Plan de despacho",
            "Ruta sugerida",
        ]
    )

    with tabs[0]:
        render_summary(orders, orders_error)

    with tabs[1]:
        render_order_registration()

    with tabs[2]:
        render_orders_list(orders, orders_error)

    with tabs[3]:
        render_status_view(orders)

    with tabs[4]:
        render_dispatch_plan()

    with tabs[5]:
        render_route_view()


if __name__ == "__main__":
    main()