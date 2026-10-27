"""Acceso de solo lectura a CuentaCorriente. El saldo se actualiza
exclusivamente desde FacturaRepository/PagoRepository, dentro de la misma
transacción que la factura/pago que lo origina (ver esos repositorios) —
nunca se escribe acá directamente, para que el saldo no pueda quedar
desincronizado del historial de facturas/pagos que lo explica."""
import logging

from mysql.connector import Error as MySQLError

from app.core.exceptions import RepositoryError
from app.db.mysql import get_cursor
from app.domain.cuenta_corriente import CuentaCorriente

logger = logging.getLogger(__name__)


def _row_to_cuenta(row: dict) -> CuentaCorriente:
    return CuentaCorriente(
        id_cuenta=row["id_cuenta"],
        id_cliente=row["id_cliente"],
        saldo=float(row["saldo"]),
        fecha_actualizacion=row["fecha_actualizacion"],
    )


class CuentaCorrienteRepository:
    def obtener_por_cliente(self, id_cliente: int) -> CuentaCorriente | None:
        try:
            with get_cursor() as cursor:
                cursor.execute("SELECT * FROM cuenta_corriente WHERE id_cliente = %s", (id_cliente,))
                row = cursor.fetchone()
                return _row_to_cuenta(row) if row else None
        except MySQLError as e:
            logger.exception("Error obteniendo cuenta corriente")
            raise RepositoryError(f"No se pudo obtener la cuenta corriente: {e}") from e

    def listar(self) -> list[CuentaCorriente]:
        try:
            with get_cursor() as cursor:
                cursor.execute("SELECT * FROM cuenta_corriente ORDER BY saldo DESC")
                return [_row_to_cuenta(row) for row in cursor.fetchall()]
        except MySQLError as e:
            logger.exception("Error listando cuentas corrientes")
            raise RepositoryError(f"No se pudo listar las cuentas corrientes: {e}") from e
