from dataclasses import dataclass
from datetime import datetime


@dataclass
class Pago:
    id_factura: int
    monto: float
    medio_pago: str
    fecha: datetime | None = None
    id_pago: int | None = None
