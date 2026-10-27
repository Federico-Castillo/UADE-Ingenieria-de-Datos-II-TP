from dataclasses import dataclass


@dataclass
class OperadorLogistico:
    razon_social: str
    cuit: str
    email: str
    telefono: str | None = None
    estado: str = "activo"
    id_operador_logistico: int | None = None
