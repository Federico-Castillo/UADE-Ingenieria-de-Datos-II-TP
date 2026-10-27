from dataclasses import dataclass
from datetime import date


@dataclass
class SensorIoT:
    id_contenedor: int
    tipo: str
    fabricante: str | None = None
    fecha_instalacion: date | None = None
    estado: str = "activo"
    id_sensor: int | None = None
