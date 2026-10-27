from dataclasses import dataclass
from datetime import datetime


@dataclass
class CierreCuentaCorriente:
    id_cliente: int
    periodo: str  # 'YYYY-MM'
    saldo_al_cierre: float = 0.0
    fecha_cierre: datetime | None = None
    id_cierre: int | None = None
