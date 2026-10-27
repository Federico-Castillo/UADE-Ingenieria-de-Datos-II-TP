from dataclasses import dataclass
from datetime import datetime


@dataclass
class CierreCuentaCorrientePagable:
    periodo: str  # 'YYYY-MM'
    id_proveedor: int | None = None
    id_operador_logistico: int | None = None
    saldo_al_cierre: float = 0.0
    fecha_cierre: datetime | None = None
    id_cierre: int | None = None
