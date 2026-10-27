from dataclasses import dataclass
from datetime import datetime

# Qué campo de LecturaSensor corresponde al "tipo" de un SensorIoT (MySQL).
# Compartido entre LecturaSensorService (evalúa Reglas contra este campo) y
# el simulador de sensores IoT (genera valores para este campo) — debe ser
# el mismo mapeo en los dos lados o el simulador podría generar anomalías
# que el Service nunca evalúa.
CAMPO_POR_TIPO_SENSOR = {
    "temperatura": "temperatura",
    "humedad": "humedad",
    "vibracion": "vibracion",
    "bateria": "nivel_bateria",
}


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
