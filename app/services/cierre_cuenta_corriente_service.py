"""Proceso periódico "cierre mensual de cuentas corrientes": toma el saldo
vivo de cuenta_corriente/cuenta_corriente_pagable al momento de ejecutarse y
registra un snapshot por período (CierreCuentaCorriente/
CierreCuentaCorrientePagable). No resetea ni modifica el saldo real — una
cuenta corriente comercial no se "cancela" al cerrar el mes, el saldo sigue
acumulado hasta que se paga; el cierre es el resumen histórico de ese
período, pensado para correrse una vez por mes (o volver a correrse para
corregir/regenerar el snapshot de un período ya cerrado)."""
import logging
import re
from datetime import datetime

from app.core.exceptions import ValidationError
from app.domain.cierre_cuenta_corriente import CierreCuentaCorriente
from app.domain.cierre_cuenta_corriente_pagable import CierreCuentaCorrientePagable
from app.repositories.cierre_cuenta_corriente_pagable_repository import CierreCuentaCorrientePagableRepository
from app.repositories.cierre_cuenta_corriente_repository import CierreCuentaCorrienteRepository
from app.repositories.cuenta_corriente_pagable_repository import CuentaCorrientePagableRepository
from app.repositories.cuenta_corriente_repository import CuentaCorrienteRepository

logger = logging.getLogger(__name__)

_PATRON_PERIODO = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def periodo_actual() -> str:
    return datetime.now().strftime("%Y-%m")


def _validar_periodo(periodo: str) -> None:
    if not _PATRON_PERIODO.match(periodo):
        raise ValidationError(f"Período inválido: '{periodo}'. Formato esperado: 'YYYY-MM'.")


class CierreCuentaCorrienteService:
    def __init__(
        self,
        cuenta_repo: CuentaCorrienteRepository | None = None,
        cuenta_pagable_repo: CuentaCorrientePagableRepository | None = None,
        cierre_repo: CierreCuentaCorrienteRepository | None = None,
        cierre_pagable_repo: CierreCuentaCorrientePagableRepository | None = None,
    ):
        self._cuenta_repo = cuenta_repo or CuentaCorrienteRepository()
        self._cuenta_pagable_repo = cuenta_pagable_repo or CuentaCorrientePagableRepository()
        self._cierre_repo = cierre_repo or CierreCuentaCorrienteRepository()
        self._cierre_pagable_repo = cierre_pagable_repo or CierreCuentaCorrientePagableRepository()

    def ejecutar_cierre_mensual(self, periodo: str | None = None) -> dict:
        periodo = periodo or periodo_actual()
        _validar_periodo(periodo)

        cuentas = self._cuenta_repo.listar()
        for cuenta in cuentas:
            self._cierre_repo.registrar(cuenta.id_cliente, periodo, cuenta.saldo)

        cuentas_pagables = self._cuenta_pagable_repo.listar()
        for cuenta in cuentas_pagables:
            self._cierre_pagable_repo.registrar(
                cuenta.id_proveedor, cuenta.id_operador_logistico, periodo, cuenta.saldo
            )

        logger.info(
            "Cierre mensual ejecutado para el período %s: %s cuentas de clientes, %s cuentas pagables",
            periodo, len(cuentas), len(cuentas_pagables),
        )
        return {
            "periodo": periodo,
            "clientes_cerrados": len(cuentas),
            "pagables_cerrados": len(cuentas_pagables),
        }

    def historial_cliente(self, id_cliente: int) -> list[CierreCuentaCorriente]:
        return self._cierre_repo.listar_por_cliente(id_cliente)

    def historial_proveedor(self, id_proveedor: int) -> list[CierreCuentaCorrientePagable]:
        return self._cierre_pagable_repo.listar_por_proveedor(id_proveedor)

    def historial_operador(self, id_operador_logistico: int) -> list[CierreCuentaCorrientePagable]:
        return self._cierre_pagable_repo.listar_por_operador(id_operador_logistico)

    def historial_periodo(self, periodo: str) -> dict:
        _validar_periodo(periodo)
        return {
            "clientes": self._cierre_repo.listar_por_periodo(periodo),
            "pagables": self._cierre_pagable_repo.listar_por_periodo(periodo),
        }
