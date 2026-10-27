from dataclasses import dataclass
from datetime import datetime


@dataclass
class CuentaCorrientePagable:
    id_proveedor: int | None = None
    id_operador_logistico: int | None = None
    saldo: float = 0.0
    fecha_actualizacion: datetime | None = None
    id_cuenta_pagable: int | None = None
