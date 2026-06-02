from __future__ import annotations

import os
from typing import Any

import requests
import streamlit as st
import pandas as pd


API_BASE_URL_DEFAULT = os.getenv("LOGISTIAI_API_URL", "http://127.0.0.1:8000")


st.set_page_config(
    page_title="Panel de despacho",
    page_icon="",
    layout="wide",
)
def _load_background_css() -> None:
    """
    Carga fondo.png como base64 e lo inyecta en el CSS.
    Si el archivo no existe, aplica un degradado oscuro como fallback.
    """
    import base64

    fondo_path = "assets/fondo.png"

    if os.path.exists(fondo_path):
        with open(fondo_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        bg_css = (
            f"linear-gradient(rgba(5,10,25,0.88), rgba(5,10,25,0.92)),"
            f"url('data:image/png;base64,{b64}')"
        )
    else:
        bg_css = "linear-gradient(160deg, #020617 0%, #0f172a 50%, #082f49 100%)"

    st.markdown(f"""
<style>
.stApp {{
    background: {bg_css};
    background-size: cover;
    background-position: center;
    background-attachment: fixed;
}}

.block-container {{
    padding-top: 2rem;
    padding-bottom: 2rem;
}}

section[data-testid="stSidebar"] {{
    background: linear-gradient(180deg, #020617, #0f172a);
    border-right: 1px solid rgba(34, 211, 238, 0.25);
}}

h1, h2, h3 {{
    color: #f8fafc;
}}

p, label, span {{
    color: #e5e7eb;
}}

.kpi-card {{
    background: linear-gradient(135deg, rgba(15, 23, 42, 0.95), rgba(8, 47, 73, 0.85));
    padding: 22px;
    border-radius: 18px;
    border: 1px solid rgba(34, 211, 238, 0.45);
    box-shadow: 0 0 22px rgba(34, 211, 238, 0.16);
}}

.kpi-title {{
    font-size: 14px;
    color: #bae6fd;
    margin-bottom: 8px;
    font-weight: 600;
}}

.kpi-value {{
    font-size: 34px;
    font-weight: 800;
    color: #22d3ee;
}}

.section-card {{
    background: rgba(15, 23, 42, 0.88);
    padding: 22px;
    border-radius: 18px;
    border: 1px solid rgba(34, 211, 238, 0.35);
    margin-top: 16px;
    box-shadow: 0 0 18px rgba(14, 165, 233, 0.12);
}}

.stDataFrame {{
    background: rgba(15, 23, 42, 0.85);
    border-radius: 14px;
}}

div[data-testid="stMetric"] {{
    background: rgba(15, 23, 42, 0.82);
    border: 1px solid rgba(34, 211, 238, 0.28);
    padding: 14px;
    border-radius: 14px;
}}

.stButton > button {{
    background: linear-gradient(90deg, #0891b2, #22d3ee);
    color: #020617;
    border: none;
    border-radius: 12px;
    font-weight: 700;
}}

.stButton > button:hover {{
    background: linear-gradient(90deg, #22d3ee, #67e8f9);
    color: #020617;
}}
</style>
""", unsafe_allow_html=True)


_load_background_css()

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
        if os.path.exists("assets/logo.png"):
            st.image("assets/logo.png", width=220)

        st.markdown("")
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
            ""
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

    with col1:
       st.markdown(f"""
       <div class="kpi-card">
       <div class="kpi-title">📦 Total pedidos</div>
        <div class="kpi-value">{total_orders}</div>
       </div>
       """, unsafe_allow_html=True)

    with col2:
       st.markdown(f"""
       <div class="kpi-card">
        <div class="kpi-title">📥 Recibidos</div>
        <div class="kpi-value">{received}</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="kpi-card">
        <div class="kpi-title">⏳ Pendientes</div>
        <div class="kpi-value">{pending}</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
         st.markdown(f"""
         <div class="kpi-card">
            <div class="kpi-title">📋 Listos</div>
            <div class="kpi-value">{ready}</div>
         </div>
         """, unsafe_allow_html=True)

    with col5:
       st.markdown(f"""
       <div class="kpi-card">
        <div class="kpi-title">🚚 Planificados</div>
        <div class="kpi-value">{planned}</div>
       </div>
       """, unsafe_allow_html=True)
    st.subheader("📊 Pedidos por estado")

    if counts:
        df = pd.DataFrame(
           [
                 {"estado": status, "cantidad": amount}
                 for status, amount in sorted(counts.items())
            ]
        )

        st.bar_chart(
             df.set_index("estado")
        )
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

    pedido = orders[selected_index]

    st.markdown("### 📦 Información del pedido")

    col1, col2 = st.columns(2)

    with col1:
        st.metric("Cliente", pedido.get("cliente", "-"))
        st.metric("Zona", pedido.get("zona", "-"))
        st.metric("Estado", pedido.get("estado", "-"))

    with col2:
        st.metric("Urgencia", pedido.get("urgencia", "-"))
        st.metric("Prioridad", pedido.get("score_prioridad", "-"))
        st.metric("Dirección", pedido.get("direccion", "-"))

    st.markdown("### 🛒 Productos")

    productos = pedido.get("productos", [])

    if productos:
        productos_rows = []

        for producto in productos:
            productos_rows.append({
                "Producto": producto.get("nombre"),
                "Cantidad": producto.get("cantidad"),
                "Unidad": producto.get("unidad"),
            })

        st.dataframe(
            productos_rows,
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No hay productos registrados.")

    if pedido.get("observaciones"):
        st.markdown("### 📝 Observaciones")
        st.info(pedido.get("observaciones"))


# ============================================================
# Orden geográfico de zonas desde El Girón
# ============================================================

ROUTE_ORDER = {
    "El Girón": 0,
    "Centro Histórico": 1,
    "La Marín": 2,
    "Cumbayá": 3,
    "Tumbaco": 4,
    "Puembo": 5,
    "San Rafael": 6,
    "Sangolquí": 7,
    "Conocoto": 8,
    "Quitumbe": 9,
    "Guamaní": 10,
    "Calderón": 11,
    "Carapungo": 12,
}


def get_ready_orders(orders: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        [o for o in orders if o.get("estado") == "listo_para_despacho"],
        key=lambda o: (
            ROUTE_ORDER.get(o.get("zona"), 999),
            -(o.get("score_prioridad") or 0),
        ),
    )


def render_status_view(orders: list[dict[str, Any]]) -> None:
    st.header("Estado de pedidos")
    st.write("Monitoreo operativo de los pedidos registrados.")

    if not orders:
        st.info("No hay pedidos registrados.")
        return

    rows = orders_to_rows(orders)
    df = pd.DataFrame(rows)

    counts = count_statuses(orders)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📥 Recibidos", counts.get("recibido", 0))
    col2.metric("🚚 Listos despacho", counts.get("listo_para_despacho", 0))
    col3.metric("✅ Entregados", counts.get("entregado", 0))
    col4.metric("⚠️ Pendientes", counts.get("pendiente_datos", 0))

    st.subheader("📋 Pedidos por estado")
    st.dataframe(
        df[["id", "cliente", "zona", "urgencia", "estado", "score_prioridad"]],
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("📊 Distribución por estado")
    status_df = pd.DataFrame(
        [{"estado": k, "cantidad": v} for k, v in counts.items()]
    )

    if not status_df.empty:
        st.bar_chart(status_df.set_index("estado"))


def render_dispatch_plan() -> None:
    st.header("Plan de despacho")
    st.write(
        "Pedidos listos para despacho ordenados por cercanía geográfica desde El Girón "
        "y prioridad dentro de cada zona."
    )

    orders_payload, orders_error = api_request("GET", "/api/orders", timeout=10)

    if orders_error:
        st.error(orders_error)
        return

    orders = extract_orders(orders_payload)
    ready_orders = get_ready_orders(orders)

    if not ready_orders:
        st.info("No hay pedidos listos para despacho.")
        return

    col1, col2, col3 = st.columns(3)
    col1.metric("🚚 Pedidos en ruta", len(ready_orders))
    col2.metric("📍 Zonas", len(set(o.get("zona") for o in ready_orders)))
    col3.metric("⭐ Mayor prioridad", max(o.get("score_prioridad") or 0 for o in ready_orders))

    rows = []

    for index, order in enumerate(ready_orders, start=1):
        rows.append({
            "parada": index,
            "pedido": order.get("id"),
            "cliente": order.get("cliente"),
            "zona": order.get("zona"),
            "direccion": order.get("direccion"),
            "prioridad": order.get("score_prioridad"),
            "estado": order.get("estado"),
        })

    st.subheader("🚚 Orden sugerido de despacho")
    st.dataframe(rows, use_container_width=True, hide_index=True)

    st.subheader("📍 Pedidos por zona en esta ruta")

    zone_counts = {}

    for order in ready_orders:
        zona = order.get("zona") or "Sin zona"
        zone_counts[zona] = zone_counts.get(zona, 0) + 1

    zone_df = pd.DataFrame(
        [
            {"zona": zona, "cantidad": cantidad}
            for zona, cantidad in sorted(
                zone_counts.items(),
                key=lambda item: item[1],
                reverse=True,
            )
        ]
    )

    st.bar_chart(zone_df.set_index("zona"))

    st.info(
        ""
    )


def render_route_view() -> None:
    st.header("Ruta sugerida")

    orders_payload, orders_error = api_request("GET", "/api/orders", timeout=10)

    if orders_error:
        st.error(orders_error)
        return

    orders = extract_orders(orders_payload)
    ready_orders = get_ready_orders(orders)

    if not ready_orders:
        st.warning("No hay pedidos listos para despacho.")
        return

    st.subheader("📍 Secuencia de entrega")

    for index, order in enumerate(ready_orders, start=1):
        maps_url = (
            "https://www.google.com/maps/search/?api=1&query="
            + requests.utils.quote(
                f"{order.get('direccion') or ''} {order.get('zona') or ''}"
            )
        )

        st.markdown(f"""
        <div class="section-card">
            <h4>📍 Parada #{index}</h4>
            <p><b>📦 Pedido:</b> #{order.get("id")}</p>
            <p><b>👤 Cliente:</b> {order.get("cliente")}</p>
            <p><b>📌 Zona:</b> {order.get("zona")}</p>
            <p><b>🏠 Dirección:</b> {order.get("direccion")}</p>
            <p><b>⭐ Prioridad:</b> {order.get("score_prioridad")}</p>
            <p><b>📋 Estado:</b> {order.get("estado")}</p>
            <a href="{maps_url}" target="_blank">📍 Abrir en Google Maps</a>
        </div>
        """, unsafe_allow_html=True)


# ============================================================
# Aplicación principal
# ============================================================

def main() -> None:
    init_state()
    render_sidebar()

    st.title("Panel de despacho LogistIA")
    st.caption(
        ""
    )

    orders_payload, orders_error = api_request("GET", "/api/orders", timeout=10)
    orders = extract_orders(orders_payload)

    tabs = st.tabs(
        [
            "Resumen general",
            "Lista de pedidos",
            "Estado de pedidos",
            "Plan de despacho",
            "Ruta sugerida",
        ]
    )

    with tabs[0]:
       render_summary(orders, orders_error)

    with tabs[1]:
       render_orders_list(orders, orders_error)

    with tabs[2]:
        render_status_view(orders)

    with tabs[3]:
        render_dispatch_plan()

    with tabs[4]:
        render_route_view()

if __name__ == "__main__":
    main()