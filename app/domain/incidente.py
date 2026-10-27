from dataclasses import dataclass
from datetime import datetime


@dataclass
class Incidente:
    id_envio: int
    tipo: str
    severidad: str
    descripcion: str = ""
    estado: str = "abierto"
    fecha: datetime | None = None
    id_incidente: str | None = None
