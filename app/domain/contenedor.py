from dataclasses import dataclass


@dataclass
class Contenedor:
    codigo_internacional: str
    tipo: str
    capacidad: float
    estado: str = "disponible"
    id_contenedor: int | None = None
