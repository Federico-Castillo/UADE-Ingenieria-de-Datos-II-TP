from dataclasses import dataclass


@dataclass
class Vehiculo:
    tipo: str
    identificacion: str
    empresa_operadora: str
    estado: str = "disponible"
    id_vehiculo: int | None = None
