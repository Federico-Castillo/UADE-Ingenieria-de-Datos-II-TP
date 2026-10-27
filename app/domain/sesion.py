from dataclasses import dataclass


@dataclass
class Sesion:
    id_usuario: int
    fecha_inicio: str
    estado: str = "activa"
    fecha_fin: str | None = None
    id_sesion: str | None = None
