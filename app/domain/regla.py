from dataclasses import dataclass
from datetime import datetime


@dataclass
class Regla:
    nombre: str
    tipo_sensor: str
    operador_comparacion: str
    valor_umbral: float
    severidad: str
    id_usuario_creador: int
    estado: str = "activa"
    fecha_creacion: datetime | None = None
    id_regla: int | None = None
