"""Acceso a datos de Contenedor contra MySQL (SQL parametrizado, sin ORM)."""
import logging

from mysql.connector import Error as MySQLError

from app.core.exceptions import DuplicateError, RepositoryError
from app.db.mysql import get_cursor, transaction
from app.domain.contenedor import Contenedor

logger = logging.getLogger(__name__)

_MYSQL_DUPLICATE_ENTRY = 1062
_MYSQL_ROW_IS_REFERENCED = 1451


def _row_to_contenedor(row: dict) -> Contenedor:
    return Contenedor(
        id_contenedor=row["id_contenedor"],
        codigo_internacional=row["codigo_internacional"],
        tipo=row["tipo"],
        capacidad=float(row["capacidad"]),
        estado=row["estado"],
    )


class ContenedorRepository:
    def crear(self, contenedor: Contenedor) -> int:
        try:
            with transaction() as cursor:
                cursor.execute(
                    """
                    INSERT INTO contenedor (codigo_internacional, tipo, capacidad, estado)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (contenedor.codigo_internacional, contenedor.tipo, contenedor.capacidad, contenedor.estado),
                )
                id_contenedor = cursor.lastrowid
                logger.info("Contenedor creado id=%s", id_contenedor)
                return id_contenedor
        except MySQLError as e:
            if e.errno == _MYSQL_DUPLICATE_ENTRY:
                logger.warning("Alta de contenedor duplicada: %s", e)
                raise DuplicateError(
                    f"Ya existe un contenedor con el código {contenedor.codigo_internacional}."
                ) from e
            logger.exception("Error creando contenedor")
            raise RepositoryError(f"No se pudo crear el contenedor: {e}") from e

    def obtener_por_id(self, id_contenedor: int) -> Contenedor | None:
        try:
            with get_cursor() as cursor:
                cursor.execute("SELECT * FROM contenedor WHERE id_contenedor = %s", (id_contenedor,))
                row = cursor.fetchone()
                return _row_to_contenedor(row) if row else None
        except MySQLError as e:
            logger.exception("Error obteniendo contenedor por id")
            raise RepositoryError(f"No se pudo obtener el contenedor: {e}") from e

    def obtener_por_codigo(self, codigo_internacional: str) -> Contenedor | None:
        try:
            with get_cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM contenedor WHERE codigo_internacional = %s", (codigo_internacional,)
                )
                row = cursor.fetchone()
                return _row_to_contenedor(row) if row else None
        except MySQLError as e:
            logger.exception("Error obteniendo contenedor por código")
            raise RepositoryError(f"No se pudo obtener el contenedor: {e}") from e

    def listar(self) -> list[Contenedor]:
        try:
            with get_cursor() as cursor:
                cursor.execute("SELECT * FROM contenedor ORDER BY codigo_internacional")
                return [_row_to_contenedor(row) for row in cursor.fetchall()]
        except MySQLError as e:
            logger.exception("Error listando contenedores")
            raise RepositoryError(f"No se pudo listar los contenedores: {e}") from e

    def buscar(self, texto: str) -> list[Contenedor]:
        try:
            with get_cursor() as cursor:
                patron = f"%{texto}%"
                cursor.execute(
                    "SELECT * FROM contenedor WHERE codigo_internacional LIKE %s OR tipo LIKE %s ORDER BY codigo_internacional",
                    (patron, patron),
                )
                return [_row_to_contenedor(row) for row in cursor.fetchall()]
        except MySQLError as e:
            logger.exception("Error buscando contenedores")
            raise RepositoryError(f"No se pudo buscar contenedores: {e}") from e

    def actualizar(self, contenedor: Contenedor) -> None:
        try:
            with transaction() as cursor:
                cursor.execute(
                    """
                    UPDATE contenedor
                    SET codigo_internacional = %s, tipo = %s, capacidad = %s, estado = %s
                    WHERE id_contenedor = %s
                    """,
                    (
                        contenedor.codigo_internacional,
                        contenedor.tipo,
                        contenedor.capacidad,
                        contenedor.estado,
                        contenedor.id_contenedor,
                    ),
                )
            logger.info("Contenedor actualizado id=%s", contenedor.id_contenedor)
        except MySQLError as e:
            if e.errno == _MYSQL_DUPLICATE_ENTRY:
                logger.warning("Actualización de contenedor duplicada: %s", e)
                raise DuplicateError(
                    f"Ya existe otro contenedor con el código {contenedor.codigo_internacional}."
                ) from e
            logger.exception("Error actualizando contenedor")
            raise RepositoryError(f"No se pudo actualizar el contenedor: {e}") from e

    def eliminar(self, id_contenedor: int) -> None:
        """Baja física: contenedor no tiene flag de estado persistente para
        'dado de baja' en el enunciado (su `estado` es operativo: disponible/
        en_uso/etc). La FK fk_sensor_contenedor con ON DELETE RESTRICT protege
        contra borrar un contenedor con sensores asociados."""
        try:
            with transaction() as cursor:
                cursor.execute("DELETE FROM contenedor WHERE id_contenedor = %s", (id_contenedor,))
            logger.info("Contenedor eliminado id=%s", id_contenedor)
        except MySQLError as e:
            if e.errno == _MYSQL_ROW_IS_REFERENCED:
                logger.warning("Intento de borrar contenedor en uso: %s", e)
                raise RepositoryError(
                    "No se puede eliminar el contenedor: tiene sensores asociados."
                ) from e
            logger.exception("Error eliminando contenedor")
            raise RepositoryError(f"No se pudo eliminar el contenedor: {e}") from e
