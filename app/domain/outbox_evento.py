from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class OutboxEvento:
    entidad: str
    id_entidad: int
    tipo_evento: str
    payload: dict = field(default_factory=dict)
    estado: str = "pendiente"
    intentos: int = 0
    fecha_creacion: datetime | None = None
    fecha_procesado: datetime | None = None
    id_evento: str | None = None
