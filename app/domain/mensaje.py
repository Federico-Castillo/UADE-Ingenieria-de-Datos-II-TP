from dataclasses import dataclass
from datetime import datetime


@dataclass
class Mensaje:
    id_remitente: int
    contenido: str
    tipo: str  # "privado" o "grupal"
    id_destinatario: int | None = None
    id_grupo: str | None = None
    fecha_hora: datetime | None = None
    id_mensaje: str | None = None
