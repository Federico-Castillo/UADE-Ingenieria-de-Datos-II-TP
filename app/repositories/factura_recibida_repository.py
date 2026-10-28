"""Acceso a datos de FacturaRecibida contra MySQL. El alta es transaccional:
inserta la factura y actualiza (o crea) la cuenta_corriente_pagable del
proveedor U operador logístico en la MISMA transacción — mismo criterio que
FacturaRepository (lado cliente). El INSERT ... ON DUPLICATE KEY UPDATE
funciona igual acá aunque haya dos UNIQUE KEY (uq_cuentapagable_proveedor y
uq_cuentapagable_operador): como id_proveedor/id_operador_logistico son
mutuamente excluyentes, solo una de las dos puede matchear, y MySQL no cuenta
NULL como duplicado en ninguna UNIQUE KEY."""
import logging

from mysql.connector import Error as MySQLError

from app.core.exceptions import RepositoryError
from app.db.mysql import get_cursor, transaction
from app.domain.factura_recibida import FacturaRecibida

logger = logging.getLogger(__name__)


def _row_to_factura(row: dict) -> FacturaRecibida:
    return FacturaRecibida(
        id_factura_recibida=row["id_factura_recibida"],
        id_proveedor=row["id_proveedor"],
        id_operador_logistico=row["id_operador_logistico"],
        importe_total=float(row["importe_total"]),
        estado=row["estado"],
        fecha_emision=row["fecha_emision"],
    )


class FacturaRecibidaRepository:
    def crear(self, factura: FacturaRecibida) -> int:
        try:
            with transaction() as cursor:
                cursor.execute(
                    """
                    INSERT INTO factura_recibida
                        (id_proveedor, id_operador_logistico, importe_total, estado)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (
                        factura.id_proveedor,
                        factura.id_operador_logistico,
                        factura.importe_total,
                        factura.estado,
                    ),
                )
                id_factura = cursor.lastrowid
                cursor.execute(
                    """
                    INSERT INTO cuenta_corriente_pagable (id_proveedor, id_operador_logistico, saldo)
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        saldo = saldo + VALUES(saldo),
                        fecha_actualizacion = CURRENT_TIMESTAMP
                    """,
                    (factura.id_proveedor, factura.id_operador_logistico, factura.importe_total),
                )
                logger.info(
                    "Factura recibida creada id=%s id_proveedor=%s id_operador_logistico=%s importe_total=%s",
                    id_factura, factura.id_proveedor, factura.id_operador_logistico, factura.importe_total,
                )
                return id_factura
        except MySQLError as e:
            logger.exception("Error creando factura recibida")
            raise RepositoryError(f"No se pudo crear la factura recibida: {e}") from e

    def obtener_por_id(self, id_factura_recibida: int) -> FacturaRecibida | None:
        try:
            with get_cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM factura_recibida WHERE id_factura_recibida = %s", (id_factura_recibida,)
                )
                row = cursor.fetchone()
                return _row_to_factura(row) if row else None
        except MySQLError as e:
            logger.exception("Error obteniendo factura recibida por id")
            raise RepositoryError(f"No se pudo obtener la factura recibida: {e}") from e

    def listar(self) -> list[FacturaRecibida]:
        try:
            with get_cursor() as cursor:
                cursor.execute("SELECT * FROM factura_recibida ORDER BY fecha_emision DESC")
                return [_row_to_factura(row) for row in cursor.fetchall()]
        except MySQLError as e:
            logger.exception("Error listando facturas recibidas")
            raise RepositoryError(f"No se pudo listar las facturas recibidas: {e}") from e

    def listar_por_proveedor(self, id_proveedor: int) -> list[FacturaRecibida]:
        try:
            with get_cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM factura_recibida WHERE id_proveedor = %s ORDER BY fecha_emision DESC",
                    (id_proveedor,),
                )
                return [_row_to_factura(row) for row in cursor.fetchall()]
        except MySQLError as e:
            logger.exception("Error listando facturas recibidas de un proveedor")
            raise RepositoryError(f"No se pudo listar las facturas del proveedor: {e}") from e

    def listar_por_operador(self, id_operador_logistico: int) -> list[FacturaRecibida]:
        try:
            with get_cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM factura_recibida WHERE id_operador_logistico = %s ORDER BY fecha_emision DESC",
                    (id_operador_logistico,),
                )
                return [_row_to_factura(row) for row in cursor.fetchall()]
        except MySQLError as e:
            logger.exception("Error listando facturas recibidas de un operador")
            raise RepositoryError(f"No se pudo listar las facturas del operador: {e}") from e
