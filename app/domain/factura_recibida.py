from dataclasses import dataclass
from datetime import datetime


@dataclass
class FacturaRecibida:
    """id_proveedor e id_operador_logistico son mutuamente excluyentes:
    exactamente uno de los dos debe estar seteado (ver CHECK
    chk_facturarecibida_emisor en el esquema)."""
    importe_total: float
    id_proveedor: int | None = None
    id_operador_logistico: int | None = None
    estado: str = "pendiente"
    fecha_emision: datetime | None = None
    id_factura_recibida: int | None = None
