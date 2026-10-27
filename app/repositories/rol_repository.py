"""Acceso a datos de Rol contra MySQL."""
import logging

from mysql.connector import Error as MySQLError

from app.core.exceptions import RepositoryError
from app.db.mysql import get_cursor, transaction
from app.domain.rol import Rol

logger = logging.getLogger(__name__)


def _row_to_rol(row: dict) -> Rol:
    return Rol(
        id_rol=row["id_rol"],
        descripcion=row["descripcion"],
        nivel_permisos=row["nivel_permisos"],
    )


class RolRepository:
    def crear(self, rol: Rol) -> int:
        try:
            with transaction() as cursor:
                cursor.execute(
                    "INSERT INTO rol (descripcion, nivel_permisos) VALUES (%s, %s)",
                    (rol.descripcion, rol.nivel_permisos),
                )
                return cursor.lastrowid
        except MySQLError as e:
            logger.exception("Error creando rol")
            raise RepositoryError(f"No se pudo crear el rol: {e}") from e

    def obtener_por_id(self, id_rol: int) -> Rol | None:
        try:
            with get_cursor() as cursor:
                cursor.execute("SELECT * FROM rol WHERE id_rol = %s", (id_rol,))
                row = cursor.fetchone()
                return _row_to_rol(row) if row else None
        except MySQLError as e:
            logger.exception("Error obteniendo rol por id")
            raise RepositoryError(f"No se pudo obtener el rol: {e}") from e

    def listar(self) -> list[Rol]:
        try:
            with get_cursor() as cursor:
                cursor.execute("SELECT * FROM rol ORDER BY nivel_permisos DESC, descripcion")
                return [_row_to_rol(row) for row in cursor.fetchall()]
        except MySQLError as e:
            logger.exception("Error listando roles")
            raise RepositoryError(f"No se pudo listar los roles: {e}") from e

    def actualizar(self, rol: Rol) -> None:
        try:
            with transaction() as cursor:
                cursor.execute(
                    "UPDATE rol SET descripcion = %s, nivel_permisos = %s WHERE id_rol = %s",
                    (rol.descripcion, rol.nivel_permisos, rol.id_rol),
                )
        except MySQLError as e:
            logger.exception("Error actualizando rol")
            raise RepositoryError(f"No se pudo actualizar el rol: {e}") from e

    def eliminar(self, id_rol: int) -> None:
        """Baja física: rol no tiene flag de estado en el modelo, y la FK
        fk_usuario_rol con ON DELETE RESTRICT ya protege contra borrar un rol
        en uso (MySQL lo rechaza si hay usuarios asociados)."""
        try:
            with transaction() as cursor:
                cursor.execute("DELETE FROM rol WHERE id_rol = %s", (id_rol,))
        except MySQLError as e:
            if e.errno == 1451:  # ER_ROW_IS_REFERENCED_2 (violación de FK RESTRICT)
                logger.warning("Intento de borrar rol en uso: %s", e)
                raise RepositoryError(
                    "No se puede eliminar el rol: tiene usuarios asociados."
                ) from e
            logger.exception("Error eliminando rol")
            raise RepositoryError(f"No se pudo eliminar el rol: {e}") from e
