#DEFINICION OFICIAL de la estructura JSON(IDIOMA JASON)
from pydantic import BaseModel, Field
from typing import List, Optional


class ProductSchema(BaseModel):
    nombre: Optional[str] = None
    cantidad: Optional[float] = None
    unidad: Optional[str] = None


class OrderRequestSchema(BaseModel):
    message: str = Field(..., min_length=5)


class OrderResponseSchema(BaseModel):
    cliente: Optional[str] = None
    telefono: Optional[str] = None
    zona: Optional[str] = None
    direccion: Optional[str] = None
    productos: List[ProductSchema] = []
    urgencia: Optional[str] = "media"
    hora_limite: Optional[str] = None
    observaciones: Optional[str] = None
    estado: Optional[str] = "pendiente_datos"
    score_prioridad: Optional[int] = None
    id: Optional[int] = None
    errores: Optional[List[str]] = None


class RouteStopSchema(BaseModel):
    order_id: Optional[int] = None
    cliente: Optional[str] = None
    zona: Optional[str] = None
    priority: Optional[int] = None


class RouteSchema(BaseModel):
    method: str
    fallback_used: bool
    total_distance_km: float
    total_time_min: int
    stops: List[RouteStopSchema] = []


class DispatchResponseSchema(BaseModel):
    total_orders: int
    route: RouteSchema
    message: str


class StatusResponseSchema(BaseModel):
    recibido: int
    pendiente_datos: int
    listo_para_despacho: int
    planificado: int
    en_ruta: int
    entregado: int
    cancelado: int