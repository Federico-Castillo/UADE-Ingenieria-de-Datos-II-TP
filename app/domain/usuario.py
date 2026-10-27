from dataclasses import dataclass
from datetime import datetime


@dataclass
class Usuario:
    nombre: str
    apellido: str
    email: str
    id_rol: int
    id_cliente: int | None = None
    password_hash: str = ""
    estado: str = "activo"
    fecha_registro: datetime | None = None
    id_usuario: int | None = None
