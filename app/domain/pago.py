from dataclasses import dataclass
from datetime import datetime


# Única fuente de los medios de pago: la usan los services (validación), la CLI
# y los desplegables de la UI, tanto para Pago como para PagoEmitido.
MEDIOS_PAGO_VALIDOS = ("efectivo", "transferencia")


@dataclass
class Pago:
    id_factura: int
    monto: float
    medio_pago: str
    fecha: datetime | None = None
    id_pago: int | None = None
