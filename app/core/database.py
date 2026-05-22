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
    pass


def save_order(order: dict) -> dict:
    pass

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