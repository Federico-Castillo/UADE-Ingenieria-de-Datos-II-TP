"""Acceso a datos de Reporte contra MySQL (SQL parametrizado, sin ORM)."""
import logging

from mysql.connector import Error as MySQLError

from app.core.exceptions import RepositoryError
from app.db.mysql import get_cursor, transaction
from app.domain.reporte import Reporte

logger = logging.getLogger(__name__)


def _row_to_reporte(row: dict) -> Reporte:
    return Reporte(
        id_reporte=row["id_reporte"],
        id_usuario=row["id_usuario"],
        tipo=row["tipo"],
        formato=row["formato"],
        estado=row["estado"],
        fecha_generacion=row["fecha_generacion"],
    )


class ReporteRepository:
    def crear(self, reporte: Reporte) -> int:
        try:
            with transaction() as cursor:
                cursor.execute(
                    "INSERT INTO reporte (id_usuario, tipo, formato, estado) VALUES (%s, %s, %s, %s)",
                    (reporte.id_usuario, reporte.tipo, reporte.formato, reporte.estado),
                )
                return cursor.lastrowid
        except MySQLError as e:
            logger.exception("Error creando reporte")
            raise RepositoryError(f"No se pudo crear el reporte: {e}") from e

    def obtener_por_id(self, id_reporte: int) -> Reporte | None:
        try:
            with get_cursor() as cursor:
                cursor.execute("SELECT * FROM reporte WHERE id_reporte = %s", (id_reporte,))
                row = cursor.fetchone()
                return _row_to_reporte(row) if row else None
        except MySQLError as e:
            logger.exception("Error obteniendo reporte por id")
            raise RepositoryError(f"No se pudo obtener el reporte: {e}") from e

    def listar(self) -> list[Reporte]:
        try:
            with get_cursor() as cursor:
                cursor.execute("SELECT * FROM reporte ORDER BY fecha_generacion DESC")
                return [_row_to_reporte(row) for row in cursor.fetchall()]
        except MySQLError as e:
            logger.exception("Error listando reportes")
            raise RepositoryError(f"No se pudo listar los reportes: {e}") from e

    def listar_por_usuario(self, id_usuario: int) -> list[Reporte]:
        try:
            with get_cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM reporte WHERE id_usuario = %s ORDER BY fecha_generacion DESC", (id_usuario,)
                )
                return [_row_to_reporte(row) for row in cursor.fetchall()]
        except MySQLError as e:
            logger.exception("Error listando reportes de un usuario")
            raise RepositoryError(f"No se pudo listar los reportes del usuario: {e}") from e

    def eliminar(self, id_reporte: int) -> None:
        try:
            with transaction() as cursor:
                cursor.execute("DELETE FROM reporte WHERE id_reporte = %s", (id_reporte,))
        except MySQLError as e:
            logger.exception("Error eliminando reporte")
            raise RepositoryError(f"No se pudo eliminar el reporte: {e}") from e
