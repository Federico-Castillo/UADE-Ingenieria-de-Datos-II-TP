from dataclasses import dataclass
from datetime import datetime


@dataclass
class Reporte:
    id_usuario: int
    tipo: str
    formato: str
    estado: str = "generado"
    fecha_generacion: datetime | None = None
    id_reporte: int | None = None
