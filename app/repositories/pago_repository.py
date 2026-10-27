"""Acceso a datos de Pago contra MySQL. El alta es transaccional: inserta el
pago, descuenta el monto del saldo de la cuenta_corriente del cliente dueño de
la factura, y recalcula el estado de la factura (pendiente/parcial/pagada) —
todo en la misma transacción que FacturaRepository usa para el alta."""
import logging

from mysql.connector import Error as MySQLError

from app.core.exceptions import RepositoryError
from app.db.mysql import get_cursor, transaction
from app.domain.pago import Pago

logger = logging.getLogger(__name__)


def _row_to_pago(row: dict) -> Pago:
    return Pago(
        id_pago=row["id_pago"],
        id_factura=row["id_factura"],
        monto=float(row["monto"]),
        medio_pago=row["medio_pago"],
        fecha=row["fecha"],
    )


class PagoRepository:
    def crear(self, pago: Pago) -> int:
        try:
            with transaction() as cursor:
                cursor.execute(
                    "SELECT id_cliente, importe_total FROM factura WHERE id_factura = %s FOR UPDATE",
                    (pago.id_factura,),
                )
                factura_row = cursor.fetchone()
                if factura_row is None:
                    raise RepositoryError(f"No existe la factura con id {pago.id_factura}.")

                cursor.execute(
                    "INSERT INTO pago (id_factura, monto, medio_pago) VALUES (%s, %s, %s)",
                    (pago.id_factura, pago.monto, pago.medio_pago),
                )
                id_pago = cursor.lastrowid

                cursor.execute(
                    """
                    UPDATE cuenta_corriente
                    SET saldo = saldo - %s, fecha_actualizacion = CURRENT_TIMESTAMP
                    WHERE id_cliente = %s
                    """,
                    (pago.monto, factura_row["id_cliente"]),
                )

                cursor.execute(
                    "SELECT COALESCE(SUM(monto), 0) AS total_pagado FROM pago WHERE id_factura = %s",
                    (pago.id_factura,),
                )
                total_pagado = cursor.fetchone()["total_pagado"]
                nuevo_estado = "pagada" if total_pagado >= factura_row["importe_total"] else "parcial"
                cursor.execute(
                    "UPDATE factura SET estado = %s WHERE id_factura = %s", (nuevo_estado, pago.id_factura)
                )

                return id_pago
        except MySQLError as e:
            logger.exception("Error creando pago")
            raise RepositoryError(f"No se pudo crear el pago: {e}") from e

    def obtener_por_id(self, id_pago: int) -> Pago | None:
        try:
            with get_cursor() as cursor:
                cursor.execute("SELECT * FROM pago WHERE id_pago = %s", (id_pago,))
                row = cursor.fetchone()
                return _row_to_pago(row) if row else None
        except MySQLError as e:
            logger.exception("Error obteniendo pago por id")
            raise RepositoryError(f"No se pudo obtener el pago: {e}") from e

    def listar_por_factura(self, id_factura: int) -> list[Pago]:
        try:
            with get_cursor() as cursor:
                cursor.execute("SELECT * FROM pago WHERE id_factura = %s ORDER BY fecha", (id_factura,))
                return [_row_to_pago(row) for row in cursor.fetchall()]
        except MySQLError as e:
            logger.exception("Error listando pagos de una factura")
            raise RepositoryError(f"No se pudo listar los pagos de la factura: {e}") from e
