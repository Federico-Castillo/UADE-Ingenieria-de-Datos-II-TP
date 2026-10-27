"""Acceso a datos de CierreCuentaCorrientePagable: snapshots del cierre
mensual, lado pagable (proveedores/operadores logísticos). Mismo criterio que
CierreCuentaCorrienteRepository (lado cliente); el upsert funciona igual que
en FacturaRecibidaRepository aunque haya dos UNIQUE KEY compuestas, porque
id_proveedor/id_operador_logistico son mutuamente excluyentes y MySQL no
cuenta NULL como duplicado en ninguna UNIQUE KEY."""
import logging

from mysql.connector import Error as MySQLError

from app.core.exceptions import RepositoryError
from app.db.mysql import get_cursor, transaction
from app.domain.cierre_cuenta_corriente_pagable import CierreCuentaCorrientePagable

logger = logging.getLogger(__name__)


def _row_to_cierre(row: dict) -> CierreCuentaCorrientePagable:
    return CierreCuentaCorrientePagable(
        id_cierre=row["id_cierre"],
        id_proveedor=row["id_proveedor"],
        id_operador_logistico=row["id_operador_logistico"],
        periodo=row["periodo"],
        saldo_al_cierre=float(row["saldo_al_cierre"]),
        fecha_cierre=row["fecha_cierre"],
    )


class CierreCuentaCorrientePagableRepository:
    def registrar(
        self, id_proveedor: int | None, id_operador_logistico: int | None, periodo: str, saldo: float
    ) -> None:
        try:
            with transaction() as cursor:
                cursor.execute(
                    """
                    INSERT INTO cierre_cuenta_corriente_pagable
                        (id_proveedor, id_operador_logistico, periodo, saldo_al_cierre)
                    VALUES (%s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        saldo_al_cierre = VALUES(saldo_al_cierre),
                        fecha_cierre = CURRENT_TIMESTAMP
                    """,
                    (id_proveedor, id_operador_logistico, periodo, saldo),
                )
        except MySQLError as e:
            logger.exception("Error registrando cierre de cuenta corriente pagable")
            raise RepositoryError(f"No se pudo registrar el cierre: {e}") from e

    def listar_por_proveedor(self, id_proveedor: int) -> list[CierreCuentaCorrientePagable]:
        try:
            with get_cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM cierre_cuenta_corriente_pagable WHERE id_proveedor = %s ORDER BY periodo DESC",
                    (id_proveedor,),
                )
                return [_row_to_cierre(row) for row in cursor.fetchall()]
        except MySQLError as e:
            logger.exception("Error listando cierres de un proveedor")
            raise RepositoryError(f"No se pudo listar los cierres del proveedor: {e}") from e

    def listar_por_operador(self, id_operador_logistico: int) -> list[CierreCuentaCorrientePagable]:
        try:
            with get_cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM cierre_cuenta_corriente_pagable "
                    "WHERE id_operador_logistico = %s ORDER BY periodo DESC",
                    (id_operador_logistico,),
                )
                return [_row_to_cierre(row) for row in cursor.fetchall()]
        except MySQLError as e:
            logger.exception("Error listando cierres de un operador")
            raise RepositoryError(f"No se pudo listar los cierres del operador: {e}") from e

    def listar_por_periodo(self, periodo: str) -> list[CierreCuentaCorrientePagable]:
        try:
            with get_cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM cierre_cuenta_corriente_pagable WHERE periodo = %s "
                    "ORDER BY id_proveedor, id_operador_logistico",
                    (periodo,),
                )
                return [_row_to_cierre(row) for row in cursor.fetchall()]
        except MySQLError as e:
            logger.exception("Error listando cierres de un período")
            raise RepositoryError(f"No se pudo listar los cierres del período: {e}") from e
