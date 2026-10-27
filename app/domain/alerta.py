from dataclasses import dataclass


@dataclass
class Alerta:
    id_sensor: int
    id_regla: int
    tipo: str
    fecha: str
    estado: str = "activa"
    id_evento: str | None = None
    id_alerta: str | None = None
