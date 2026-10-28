"""Acceso a datos de Factura contra MySQL. El alta es transaccional: inserta
la factura Y actualiza (o crea) la cuenta_corriente del cliente en la MISMA
transacción, para que el saldo nunca quede inconsistente con el historial de
facturas — exactamente la garantía ACID que justifica MySQL en propuesta.md."""
import logging

from mysql.connector import Error as MySQLError

from app.core.exceptions import RepositoryError
from app.db.mysql import get_cursor, transaction
from app.domain.factura import Factura

logger = logging.getLogger(__name__)


def _row_to_factura(row: dict) -> Factura:
    return Factura(
        id_factura=row["id_factura"],
        id_cliente=row["id_cliente"],
        importe_total=float(row["importe_total"]),
        estado=row["estado"],
        fecha_emision=row["fecha_emision"],
    )


class FacturaRepository:
    def crear(self, factura: Factura) -> int:
        try:
            with transaction() as cursor:
                cursor.execute(
                    "INSERT INTO factura (id_cliente, importe_total, estado) VALUES (%s, %s, %s)",
                    (factura.id_cliente, factura.importe_total, factura.estado),
                )
                id_factura = cursor.lastrowid
                # Upsert: crea la cuenta_corriente si es la primera factura del
                # cliente, o suma el importe al saldo existente si ya la tiene.
                cursor.execute(
                    """
                    INSERT INTO cuenta_corriente (id_cliente, saldo)
                    VALUES (%s, %s)
                    ON DUPLICATE KEY UPDATE
                        saldo = saldo + VALUES(saldo),
                        fecha_actualizacion = CURRENT_TIMESTAMP
                    """,
                    (factura.id_cliente, factura.importe_total),
                )
                logger.info("Factura creada id=%s id_cliente=%s importe_total=%s", id_factura, factura.id_cliente, factura.importe_total)
                return id_factura
        except MySQLError as e:
            logger.exception("Error creando factura")
            raise RepositoryError(f"No se pudo crear la factura: {e}") from e

    def obtener_por_id(self, id_factura: int) -> Factura | None:
        try:
            with get_cursor() as cursor:
                cursor.execute("SELECT * FROM factura WHERE id_factura = %s", (id_factura,))
                row = cursor.fetchone()
                return _row_to_factura(row) if row else None
        except MySQLError as e:
            logger.exception("Error obteniendo factura por id")
            raise RepositoryError(f"No se pudo obtener la factura: {e}") from e

    def listar(self) -> list[Factura]:
        try:
            with get_cursor() as cursor:
                cursor.execute("SELECT * FROM factura ORDER BY fecha_emision DESC")
                return [_row_to_factura(row) for row in cursor.fetchall()]
        except MySQLError as e:
            logger.exception("Error listando facturas")
            raise RepositoryError(f"No se pudo listar las facturas: {e}") from e

    def listar_por_cliente(self, id_cliente: int) -> list[Factura]:
        try:
            with get_cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM factura WHERE id_cliente = %s ORDER BY fecha_emision DESC", (id_cliente,)
                )
                return [_row_to_factura(row) for row in cursor.fetchall()]
        except MySQLError as e:
            logger.exception("Error listando facturas de un cliente")
            raise RepositoryError(f"No se pudo listar las facturas del cliente: {e}") from e

    def actualizar_estado(self, id_factura: int, estado: str) -> None:
        try:
            with transaction() as cursor:
                cursor.execute("UPDATE factura SET estado = %s WHERE id_factura = %s", (estado, id_factura))
            logger.info("Factura actualizada id=%s nuevo_estado=%s", id_factura, estado)
        except MySQLError as e:
            logger.exception("Error actualizando estado de factura")
            raise RepositoryError(f"No se pudo actualizar el estado de la factura: {e}") from e
