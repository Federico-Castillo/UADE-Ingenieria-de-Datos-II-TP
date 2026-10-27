"""Acceso de solo lectura a CuentaCorrientePagable. El saldo se actualiza
exclusivamente desde FacturaRecibidaRepository/PagoEmitidoRepository, dentro
de la misma transacción que la factura/pago que lo origina — mismo criterio
que CuentaCorrienteRepository (lado cliente)."""
import logging

from mysql.connector import Error as MySQLError

from app.core.exceptions import RepositoryError
from app.db.mysql import get_cursor
from app.domain.cuenta_corriente_pagable import CuentaCorrientePagable

logger = logging.getLogger(__name__)


def _row_to_cuenta(row: dict) -> CuentaCorrientePagable:
    return CuentaCorrientePagable(
        id_cuenta_pagable=row["id_cuenta_pagable"],
        id_proveedor=row["id_proveedor"],
        id_operador_logistico=row["id_operador_logistico"],
        saldo=float(row["saldo"]),
        fecha_actualizacion=row["fecha_actualizacion"],
    )


class CuentaCorrientePagableRepository:
    def obtener_por_proveedor(self, id_proveedor: int) -> CuentaCorrientePagable | None:
        try:
            with get_cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM cuenta_corriente_pagable WHERE id_proveedor = %s", (id_proveedor,)
                )
                row = cursor.fetchone()
                return _row_to_cuenta(row) if row else None
        except MySQLError as e:
            logger.exception("Error obteniendo cuenta corriente pagable de proveedor")
            raise RepositoryError(f"No se pudo obtener la cuenta corriente: {e}") from e

    def obtener_por_operador(self, id_operador_logistico: int) -> CuentaCorrientePagable | None:
        try:
            with get_cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM cuenta_corriente_pagable WHERE id_operador_logistico = %s",
                    (id_operador_logistico,),
                )
                row = cursor.fetchone()
                return _row_to_cuenta(row) if row else None
        except MySQLError as e:
            logger.exception("Error obteniendo cuenta corriente pagable de operador")
            raise RepositoryError(f"No se pudo obtener la cuenta corriente: {e}") from e

    def listar(self) -> list[CuentaCorrientePagable]:
        try:
            with get_cursor() as cursor:
                cursor.execute("SELECT * FROM cuenta_corriente_pagable ORDER BY saldo DESC")
                return [_row_to_cuenta(row) for row in cursor.fetchall()]
        except MySQLError as e:
            logger.exception("Error listando cuentas corrientes pagables")
            raise RepositoryError(f"No se pudo listar las cuentas corrientes: {e}") from e
