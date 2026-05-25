#DEFINICION OFICIAL de la estructura JSON(IDIOMA JASON)

from pydantic import BaseModel, Field
from typing import List, Optional


class ProductSchema(BaseModel):
    nombre: str = Field(..., min_length=1)
    cantidad: int = Field(..., gt=0)
    unidad: str = Field(..., min_length=1)


class OrderRequestSchema(BaseModel):
    message: str = Field(..., min_length=5)


class OrderResponseSchema(BaseModel):
    cliente: str
    telefono: Optional[str] = None
    zona: str
    direccion: Optional[str] = None
    productos: List[ProductSchema]
    urgencia: str
    hora_limite: Optional[str] = None
    observaciones: Optional[str] = None
    estado: str
    score_prioridad: Optional[int] = None
    id: Optional[int] = None
    errores: Optional[List[str]] = None


class RouteStopSchema(BaseModel):
    order_id: int
    cliente: str
    zona: str
    priority: int


class RouteSchema(BaseModel):
    method: str
    fallback_used: bool
    total_distance_km: float
    total_time_min: int
    stops: List[RouteStopSchema]


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