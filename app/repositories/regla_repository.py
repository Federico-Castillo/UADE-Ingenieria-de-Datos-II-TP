"""Acceso a datos de Regla contra MySQL (SQL parametrizado, sin ORM)."""
import logging

from mysql.connector import Error as MySQLError

from app.core.exceptions import RepositoryError
from app.db.mysql import get_cursor, transaction
from app.domain.regla import Regla

logger = logging.getLogger(__name__)

_MYSQL_ROW_IS_REFERENCED = 1451


def _row_to_regla(row: dict) -> Regla:
    return Regla(
        id_regla=row["id_regla"],
        nombre=row["nombre"],
        tipo_sensor=row["tipo_sensor"],
        operador_comparacion=row["operador_comparacion"],
        valor_umbral=float(row["valor_umbral"]),
        severidad=row["severidad"],
        estado=row["estado"],
        id_usuario_creador=row["id_usuario_creador"],
        fecha_creacion=row["fecha_creacion"],
    )


class ReglaRepository:
    def crear(self, regla: Regla) -> int:
        try:
            with transaction() as cursor:
                cursor.execute(
                    """
                    INSERT INTO regla
                        (nombre, tipo_sensor, operador_comparacion, valor_umbral, severidad,
                         estado, id_usuario_creador)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        regla.nombre,
                        regla.tipo_sensor,
                        regla.operador_comparacion,
                        regla.valor_umbral,
                        regla.severidad,
                        regla.estado,
                        regla.id_usuario_creador,
                    ),
                )
                return cursor.lastrowid
        except MySQLError as e:
            logger.exception("Error creando regla")
            raise RepositoryError(f"No se pudo crear la regla: {e}") from e

    def obtener_por_id(self, id_regla: int) -> Regla | None:
        try:
            with get_cursor() as cursor:
                cursor.execute("SELECT * FROM regla WHERE id_regla = %s", (id_regla,))
                row = cursor.fetchone()
                return _row_to_regla(row) if row else None
        except MySQLError as e:
            logger.exception("Error obteniendo regla por id")
            raise RepositoryError(f"No se pudo obtener la regla: {e}") from e

    def listar(self, solo_activas: bool = False) -> list[Regla]:
        try:
            with get_cursor() as cursor:
                if solo_activas:
                    cursor.execute("SELECT * FROM regla WHERE estado = 'activa' ORDER BY nombre")
                else:
                    cursor.execute("SELECT * FROM regla ORDER BY nombre")
                return [_row_to_regla(row) for row in cursor.fetchall()]
        except MySQLError as e:
            logger.exception("Error listando reglas")
            raise RepositoryError(f"No se pudo listar las reglas: {e}") from e

    def listar_por_tipo_sensor(self, tipo_sensor: str) -> list[Regla]:
        try:
            with get_cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM regla WHERE tipo_sensor = %s AND estado = 'activa' ORDER BY nombre",
                    (tipo_sensor,),
                )
                return [_row_to_regla(row) for row in cursor.fetchall()]
        except MySQLError as e:
            logger.exception("Error listando reglas por tipo de sensor")
            raise RepositoryError(f"No se pudo listar las reglas: {e}") from e

    def actualizar(self, regla: Regla) -> None:
        try:
            with transaction() as cursor:
                cursor.execute(
                    """
                    UPDATE regla
                    SET nombre = %s, tipo_sensor = %s, operador_comparacion = %s,
                        valor_umbral = %s, severidad = %s, estado = %s
                    WHERE id_regla = %s
                    """,
                    (
                        regla.nombre,
                        regla.tipo_sensor,
                        regla.operador_comparacion,
                        regla.valor_umbral,
                        regla.severidad,
                        regla.estado,
                        regla.id_regla,
                    ),
                )
        except MySQLError as e:
            logger.exception("Error actualizando regla")
            raise RepositoryError(f"No se pudo actualizar la regla: {e}") from e

    def eliminar(self, id_regla: int) -> None:
        """Baja física: no es ideal borrar reglas referenciadas por alertas
        históricas en Redis, pero Redis no tiene FK — si se requiere
        trazabilidad estricta, preferir desactivar (estado='inactiva')
        en vez de eliminar."""
        try:
            with transaction() as cursor:
                cursor.execute("DELETE FROM regla WHERE id_regla = %s", (id_regla,))
        except MySQLError as e:
            logger.exception("Error eliminando regla")
            raise RepositoryError(f"No se pudo eliminar la regla: {e}") from e
