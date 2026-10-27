"""Acceso a datos de SensorIoT contra MySQL (SQL parametrizado, sin ORM)."""
import logging

from mysql.connector import Error as MySQLError

from app.core.exceptions import RepositoryError
from app.db.mysql import get_cursor, transaction
from app.domain.sensor_iot import SensorIoT

logger = logging.getLogger(__name__)

_MYSQL_ROW_IS_REFERENCED = 1451


def _row_to_sensor(row: dict) -> SensorIoT:
    return SensorIoT(
        id_sensor=row["id_sensor"],
        id_contenedor=row["id_contenedor"],
        tipo=row["tipo"],
        fabricante=row["fabricante"],
        fecha_instalacion=row["fecha_instalacion"],
        estado=row["estado"],
    )


class SensorIoTRepository:
    def crear(self, sensor: SensorIoT) -> int:
        try:
            with transaction() as cursor:
                cursor.execute(
                    """
                    INSERT INTO sensor_iot (id_contenedor, tipo, fabricante, fecha_instalacion, estado)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (sensor.id_contenedor, sensor.tipo, sensor.fabricante, sensor.fecha_instalacion, sensor.estado),
                )
                return cursor.lastrowid
        except MySQLError as e:
            logger.exception("Error creando sensor IoT")
            raise RepositoryError(f"No se pudo crear el sensor: {e}") from e

    def obtener_por_id(self, id_sensor: int) -> SensorIoT | None:
        try:
            with get_cursor() as cursor:
                cursor.execute("SELECT * FROM sensor_iot WHERE id_sensor = %s", (id_sensor,))
                row = cursor.fetchone()
                return _row_to_sensor(row) if row else None
        except MySQLError as e:
            logger.exception("Error obteniendo sensor por id")
            raise RepositoryError(f"No se pudo obtener el sensor: {e}") from e

    def listar(self) -> list[SensorIoT]:
        try:
            with get_cursor() as cursor:
                cursor.execute("SELECT * FROM sensor_iot ORDER BY id_sensor")
                return [_row_to_sensor(row) for row in cursor.fetchall()]
        except MySQLError as e:
            logger.exception("Error listando sensores")
            raise RepositoryError(f"No se pudo listar los sensores: {e}") from e

    def listar_por_contenedor(self, id_contenedor: int) -> list[SensorIoT]:
        try:
            with get_cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM sensor_iot WHERE id_contenedor = %s ORDER BY id_sensor", (id_contenedor,)
                )
                return [_row_to_sensor(row) for row in cursor.fetchall()]
        except MySQLError as e:
            logger.exception("Error listando sensores de un contenedor")
            raise RepositoryError(f"No se pudo listar los sensores del contenedor: {e}") from e

    def actualizar(self, sensor: SensorIoT) -> None:
        try:
            with transaction() as cursor:
                cursor.execute(
                    """
                    UPDATE sensor_iot
                    SET id_contenedor = %s, tipo = %s, fabricante = %s, fecha_instalacion = %s, estado = %s
                    WHERE id_sensor = %s
                    """,
                    (
                        sensor.id_contenedor,
                        sensor.tipo,
                        sensor.fabricante,
                        sensor.fecha_instalacion,
                        sensor.estado,
                        sensor.id_sensor,
                    ),
                )
        except MySQLError as e:
            logger.exception("Error actualizando sensor")
            raise RepositoryError(f"No se pudo actualizar el sensor: {e}") from e

    def eliminar(self, id_sensor: int) -> None:
        """Baja física: no hay otras entidades (en lo ya implementado) que
        referencien un sensor con ON DELETE RESTRICT."""
        try:
            with transaction() as cursor:
                cursor.execute("DELETE FROM sensor_iot WHERE id_sensor = %s", (id_sensor,))
        except MySQLError as e:
            if e.errno == _MYSQL_ROW_IS_REFERENCED:
                logger.warning("Intento de borrar sensor en uso: %s", e)
                raise RepositoryError("No se puede eliminar el sensor: está en uso.") from e
            logger.exception("Error eliminando sensor")
            raise RepositoryError(f"No se pudo eliminar el sensor: {e}") from e
