from dataclasses import dataclass


@dataclass
class Proveedor:
    razon_social: str
    cuit: str
    email: str
    telefono: str | None = None
    direccion: str | None = None
    pais: str | None = None
    estado: str = "activo"
    id_proveedor: int | None = None
