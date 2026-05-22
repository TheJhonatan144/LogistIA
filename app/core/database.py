import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "data" / "logistiai.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)

    conn.row_factory = sqlite3.Row 

    conn.execute("PRAGMA foreign_keys = ON")

    return conn

def init_db() -> None:
    conn = get_connection()
    cursor = conn.cursor()

    # Tabla orders
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente TEXT NOT NULL,
        telefono TEXT,
        zona TEXT,
        direccion TEXT,
        urgencia TEXT,
        hora_limite TEXT,
        observaciones TEXT,
        estado TEXT NOT NULL,
        score_prioridad INTEGER DEFAULT 100,
        errores TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Tabla productos del pedido
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS order_products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        nombre TEXT NOT NULL,
        cantidad REAL NOT NULL,
        unidad TEXT NOT NULL,
        FOREIGN KEY(order_id) REFERENCES orders(id)
    )
    """)

    # Tabla zonas
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS zones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL UNIQUE,
        latitud REAL,
        longitud REAL,
        tipo TEXT,
        activo INTEGER DEFAULT 1
    )
    """)

    # Tabla logs
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event TEXT NOT NULL,
        detail TEXT NOT NULL,
        level TEXT DEFAULT 'INFO',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

        # Verificar si ya existen zonas
    cursor.execute("SELECT COUNT(*) as total FROM zones")
    total = cursor.fetchone()["total"]

    if total == 0:

        zonas = [
            ("El Girón", None, None, "bodega", 1),
            ("La Magdalena", None, None, "sector", 1),
            ("El Condado", None, None, "sector", 1),
            ("La Carolina", None, None, "sector", 1),
            ("Centro Histórico", None, None, "sector", 1),
            ("Cumbayá", None, None, "sector", 1),
            ("Tumbaco", None, None, "sector", 1),
            ("Calderón", None, None, "sector", 1),
            ("Carapungo", None, None, "sector", 1),
            ("Valle de los Chillos", None, None, "sector", 1),
            ("Sur", None, None, "sector", 1),
            ("Norte", None, None, "sector", 1),
            ("Centro", None, None, "sector", 1),
        ]

        cursor.executemany("""
            INSERT INTO zones (
                nombre,
                latitud,
                longitud,
                tipo,
                activo
            )
            VALUES (?, ?, ?, ?, ?)
        """, zonas)

    conn.commit()
    conn.close()


def save_order(order: dict) -> dict:

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO orders (
            cliente,
            telefono,
            zona,
            direccion,
            urgencia,
            hora_limite,
            observaciones,
            estado,
            score_prioridad,
            errores
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        order.get("cliente"),
        order.get("telefono"),
        order.get("zona"),
        order.get("direccion"),
        order.get("urgencia"),
        order.get("hora_limite"),
        order.get("observaciones"),
        order.get("estado", "recibido"),
        order.get("score_prioridad", 100),
        order.get("errores")
    ))

    order_id = cursor.lastrowid

    productos = order.get("productos", [])

    for producto in productos:
        cursor.execute("""
            INSERT INTO order_products (
                order_id,
                nombre,
                cantidad,
                unidad
            )
            VALUES (?, ?, ?, ?)
        """, (
            order_id,
            producto.get("nombre"),
            producto.get("cantidad"),
            producto.get("unidad")
        ))

    conn.commit()
    conn.close()

    return {
        "id": order_id,
        "cliente": order.get("cliente"),
        "telefono": order.get("telefono"),
        "zona": order.get("zona"),
        "direccion": order.get("direccion"),
        "productos": productos,
        "urgencia": order.get("urgencia"),
        "hora_limite": order.get("hora_limite"),
        "observaciones": order.get("observaciones"),
        "estado": order.get("estado", "recibido"),
        "score_prioridad": order.get("score_prioridad", 100),
        "errores": order.get("errores")
    }

def get_all_orders() -> list[dict]:
    pass

def get_status_summary() -> dict:
    pass


def get_orders_by_status(status: str) -> list[dict]:
    pass


def update_order_status(order_id: int, status: str) -> dict | None:
    pass


def save_log(event: str, detail: str) -> None:
    pass