"""Acceso a datos de Envio contra MySQL (SQL parametrizado, sin ORM)."""
import logging

from mysql.connector import Error as MySQLError

from app.core.exceptions import RepositoryError
from app.db.mysql import get_cursor, transaction
from app.domain.envio import Envio

logger = logging.getLogger(__name__)


def _row_to_envio(row: dict) -> Envio:
    return Envio(
        id_envio=row["id_envio"],
        id_cliente=row["id_cliente"],
        origen=row["origen"],
        destino=row["destino"],
        estado=row["estado"],
        prioridad=row["prioridad"],
        fecha_creacion=row["fecha_creacion"],
    )


class EnvioRepository:
    def crear(self, envio: Envio) -> int:
        try:
            with transaction() as cursor:
                cursor.execute(
                    """
                    INSERT INTO envio (id_cliente, origen, destino, estado, prioridad)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (envio.id_cliente, envio.origen, envio.destino, envio.estado, envio.prioridad),
                )
                return cursor.lastrowid
        except MySQLError as e:
            logger.exception("Error creando envío")
            raise RepositoryError(f"No se pudo crear el envío: {e}") from e

    def obtener_por_id(self, id_envio: int) -> Envio | None:
        try:
            with get_cursor() as cursor:
                cursor.execute("SELECT * FROM envio WHERE id_envio = %s", (id_envio,))
                row = cursor.fetchone()
                return _row_to_envio(row) if row else None
        except MySQLError as e:
            logger.exception("Error obteniendo envío por id")
            raise RepositoryError(f"No se pudo obtener el envío: {e}") from e

    def listar(self) -> list[Envio]:
        try:
            with get_cursor() as cursor:
                cursor.execute("SELECT * FROM envio ORDER BY fecha_creacion DESC")
                return [_row_to_envio(row) for row in cursor.fetchall()]
        except MySQLError as e:
            logger.exception("Error listando envíos")
            raise RepositoryError(f"No se pudo listar los envíos: {e}") from e

    def listar_por_cliente(self, id_cliente: int) -> list[Envio]:
        try:
            with get_cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM envio WHERE id_cliente = %s ORDER BY fecha_creacion DESC", (id_cliente,)
                )
                return [_row_to_envio(row) for row in cursor.fetchall()]
        except MySQLError as e:
            logger.exception("Error listando envíos de un cliente")
            raise RepositoryError(f"No se pudo listar los envíos del cliente: {e}") from e

    def actualizar(self, envio: Envio) -> None:
        try:
            with transaction() as cursor:
                cursor.execute(
                    """
                    UPDATE envio
                    SET id_cliente = %s, origen = %s, destino = %s, estado = %s, prioridad = %s
                    WHERE id_envio = %s
                    """,
                    (envio.id_cliente, envio.origen, envio.destino, envio.estado, envio.prioridad, envio.id_envio),
                )
        except MySQLError as e:
            logger.exception("Error actualizando envío")
            raise RepositoryError(f"No se pudo actualizar el envío: {e}") from e

    def eliminar(self, id_envio: int) -> None:
        """Baja física: no hay otra entidad implementada hasta ahora que
        referencie un Envío con ON DELETE RESTRICT."""
        try:
            with transaction() as cursor:
                cursor.execute("DELETE FROM envio WHERE id_envio = %s", (id_envio,))
        except MySQLError as e:
            logger.exception("Error eliminando envío")
            raise RepositoryError(f"No se pudo eliminar el envío: {e}") from e
