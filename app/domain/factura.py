from dataclasses import dataclass
from datetime import datetime


@dataclass
class Factura:
    id_cliente: int
    importe_total: float
    estado: str = "pendiente"
    fecha_emision: datetime | None = None
    id_factura: int | None = None
