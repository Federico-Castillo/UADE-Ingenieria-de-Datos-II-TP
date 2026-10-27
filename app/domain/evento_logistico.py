from dataclasses import dataclass
from datetime import datetime


@dataclass
class EventoLogistico:
    id_envio: int
    tipo_evento: str
    descripcion: str = ""
    ubicacion: dict | None = None
    fecha_hora: datetime | None = None
    id_evento: str | None = None
