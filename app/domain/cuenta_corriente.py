from dataclasses import dataclass
from datetime import datetime


@dataclass
class CuentaCorriente:
    id_cliente: int
    saldo: float = 0.0
    fecha_actualizacion: datetime | None = None
    id_cuenta: int | None = None
