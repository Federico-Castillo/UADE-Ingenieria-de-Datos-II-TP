from dataclasses import dataclass
from datetime import datetime


@dataclass
class PagoEmitido:
    id_factura_recibida: int
    monto: float
    medio_pago: str
    fecha: datetime | None = None
    id_pago_emitido: int | None = None
