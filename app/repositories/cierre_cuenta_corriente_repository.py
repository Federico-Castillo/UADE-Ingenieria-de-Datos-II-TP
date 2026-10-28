"""Acceso a datos de CierreCuentaCorriente: snapshots del proceso periódico de
cierre mensual (lado cliente). registrar() es un upsert por (id_cliente,
periodo) — re-ejecutar el cierre del mismo período actualiza el snapshot en
vez de duplicarlo."""
import logging

from mysql.connector import Error as MySQLError

from app.core.exceptions import RepositoryError
from app.db.mysql import get_cursor, transaction
from app.domain.cierre_cuenta_corriente import CierreCuentaCorriente

logger = logging.getLogger(__name__)


def _row_to_cierre(row: dict) -> CierreCuentaCorriente:
    return CierreCuentaCorriente(
        id_cierre=row["id_cierre"],
        id_cliente=row["id_cliente"],
        periodo=row["periodo"],
        saldo_al_cierre=float(row["saldo_al_cierre"]),
        fecha_cierre=row["fecha_cierre"],
    )


class CierreCuentaCorrienteRepository:
    def registrar(self, id_cliente: int, periodo: str, saldo: float) -> None:
        try:
            with transaction() as cursor:
                cursor.execute(
                    """
                    INSERT INTO cierre_cuenta_corriente (id_cliente, periodo, saldo_al_cierre)
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        saldo_al_cierre = VALUES(saldo_al_cierre),
                        fecha_cierre = CURRENT_TIMESTAMP
                    """,
                    (id_cliente, periodo, saldo),
                )
            logger.info("Cierre de cuenta corriente registrado id_cliente=%s periodo=%s", id_cliente, periodo)
        except MySQLError as e:
            logger.exception("Error registrando cierre de cuenta corriente")
            raise RepositoryError(f"No se pudo registrar el cierre: {e}") from e

    def listar_por_cliente(self, id_cliente: int) -> list[CierreCuentaCorriente]:
        try:
            with get_cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM cierre_cuenta_corriente WHERE id_cliente = %s ORDER BY periodo DESC",
                    (id_cliente,),
                )
                return [_row_to_cierre(row) for row in cursor.fetchall()]
        except MySQLError as e:
            logger.exception("Error listando cierres de un cliente")
            raise RepositoryError(f"No se pudo listar los cierres del cliente: {e}") from e

    def listar_por_periodo(self, periodo: str) -> list[CierreCuentaCorriente]:
        try:
            with get_cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM cierre_cuenta_corriente WHERE periodo = %s ORDER BY id_cliente",
                    (periodo,),
                )
                return [_row_to_cierre(row) for row in cursor.fetchall()]
        except MySQLError as e:
            logger.exception("Error listando cierres de un período")
            raise RepositoryError(f"No se pudo listar los cierres del período: {e}") from e
