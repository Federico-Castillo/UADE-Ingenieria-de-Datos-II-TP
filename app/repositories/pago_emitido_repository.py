"""Acceso a datos de PagoEmitido contra MySQL. El alta es transaccional:
inserta el pago, descuenta el monto del saldo de la cuenta_corriente_pagable
del titular (proveedor U operador, según a quién pertenezca la factura
recibida) y recalcula el estado de la factura — mismo criterio que
PagoRepository (lado cliente)."""
import logging

from mysql.connector import Error as MySQLError

from app.core.exceptions import RepositoryError
from app.db.mysql import get_cursor, transaction
from app.domain.pago_emitido import PagoEmitido

logger = logging.getLogger(__name__)


def _row_to_pago(row: dict) -> PagoEmitido:
    return PagoEmitido(
        id_pago_emitido=row["id_pago_emitido"],
        id_factura_recibida=row["id_factura_recibida"],
        monto=float(row["monto"]),
        medio_pago=row["medio_pago"],
        fecha=row["fecha"],
    )


class PagoEmitidoRepository:
    def crear(self, pago: PagoEmitido) -> int:
        try:
            with transaction() as cursor:
                cursor.execute(
                    """
                    SELECT id_proveedor, id_operador_logistico, importe_total
                    FROM factura_recibida WHERE id_factura_recibida = %s FOR UPDATE
                    """,
                    (pago.id_factura_recibida,),
                )
                factura_row = cursor.fetchone()
                if factura_row is None:
                    raise RepositoryError(f"No existe la factura recibida con id {pago.id_factura_recibida}.")

                cursor.execute(
                    "INSERT INTO pago_emitido (id_factura_recibida, monto, medio_pago) VALUES (%s, %s, %s)",
                    (pago.id_factura_recibida, pago.monto, pago.medio_pago),
                )
                id_pago = cursor.lastrowid

                if factura_row["id_proveedor"] is not None:
                    cursor.execute(
                        """
                        UPDATE cuenta_corriente_pagable
                        SET saldo = saldo - %s, fecha_actualizacion = CURRENT_TIMESTAMP
                        WHERE id_proveedor = %s
                        """,
                        (pago.monto, factura_row["id_proveedor"]),
                    )
                else:
                    cursor.execute(
                        """
                        UPDATE cuenta_corriente_pagable
                        SET saldo = saldo - %s, fecha_actualizacion = CURRENT_TIMESTAMP
                        WHERE id_operador_logistico = %s
                        """,
                        (pago.monto, factura_row["id_operador_logistico"]),
                    )

                cursor.execute(
                    "SELECT COALESCE(SUM(monto), 0) AS total_pagado FROM pago_emitido WHERE id_factura_recibida = %s",
                    (pago.id_factura_recibida,),
                )
                total_pagado = cursor.fetchone()["total_pagado"]
                nuevo_estado = "pagada" if total_pagado >= factura_row["importe_total"] else "parcial"
                cursor.execute(
                    "UPDATE factura_recibida SET estado = %s WHERE id_factura_recibida = %s",
                    (nuevo_estado, pago.id_factura_recibida),
                )

                logger.info(
                    "Pago emitido creado id=%s id_factura_recibida=%s monto=%s nuevo_estado_factura=%s",
                    id_pago, pago.id_factura_recibida, pago.monto, nuevo_estado,
                )
                return id_pago
        except MySQLError as e:
            logger.exception("Error creando pago emitido")
            raise RepositoryError(f"No se pudo crear el pago: {e}") from e

    def obtener_por_id(self, id_pago_emitido: int) -> PagoEmitido | None:
        try:
            with get_cursor() as cursor:
                cursor.execute("SELECT * FROM pago_emitido WHERE id_pago_emitido = %s", (id_pago_emitido,))
                row = cursor.fetchone()
                return _row_to_pago(row) if row else None
        except MySQLError as e:
            logger.exception("Error obteniendo pago emitido por id")
            raise RepositoryError(f"No se pudo obtener el pago: {e}") from e

    def listar_por_factura(self, id_factura_recibida: int) -> list[PagoEmitido]:
        try:
            with get_cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM pago_emitido WHERE id_factura_recibida = %s ORDER BY fecha",
                    (id_factura_recibida,),
                )
                return [_row_to_pago(row) for row in cursor.fetchall()]
        except MySQLError as e:
            logger.exception("Error listando pagos de una factura recibida")
            raise RepositoryError(f"No se pudo listar los pagos de la factura: {e}") from e
