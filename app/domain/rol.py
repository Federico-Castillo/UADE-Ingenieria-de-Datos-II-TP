from dataclasses import dataclass


@dataclass
class Rol:
    descripcion: str
    nivel_permisos: int = 0
    id_rol: int | None = None
