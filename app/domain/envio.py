from dataclasses import dataclass
from datetime import datetime


@dataclass
class Envio:
    id_cliente: int
    origen: str
    destino: str
    estado: str = "pendiente"
    prioridad: str = "normal"
    fecha_creacion: datetime | None = None
    id_envio: int | None = None
