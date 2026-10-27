from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class PrediccionRiesgo:
    id_envio: int
    probabilidad_demora: float
    riesgo_climatico: float = 0.0
    riesgo_operativo: float = 0.0
    features_entrada: dict = field(default_factory=dict)
    fecha_calculo: datetime | None = None
    id_prediccion: str | None = None
