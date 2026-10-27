from dataclasses import dataclass
from datetime import datetime


@dataclass
class LecturaSensor:
    id_sensor: int
    temperatura: float | None = None
    humedad: float | None = None
    vibracion: float | None = None
    gps_lat: float | None = None
    gps_lon: float | None = None
    nivel_bateria: float | None = None
    fecha_hora: datetime | None = None
    id_lectura: str | None = None
