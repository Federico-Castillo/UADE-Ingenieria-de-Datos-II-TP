"""Acceso a datos de Vehiculo contra MySQL (SQL parametrizado, sin ORM)."""
import logging

from mysql.connector import Error as MySQLError

from app.core.exceptions import DuplicateError, RepositoryError
from app.db.mysql import get_cursor, transaction
from app.domain.vehiculo import Vehiculo

logger = logging.getLogger(__name__)

_MYSQL_DUPLICATE_ENTRY = 1062


def _row_to_vehiculo(row: dict) -> Vehiculo:
    return Vehiculo(
        id_vehiculo=row["id_vehiculo"],
        tipo=row["tipo"],
        identificacion=row["identificacion"],
        empresa_operadora=row["empresa_operadora"],
        estado=row["estado"],
    )


class VehiculoRepository:
    def crear(self, vehiculo: Vehiculo) -> int:
        try:
            with transaction() as cursor:
                cursor.execute(
                    """
                    INSERT INTO vehiculo (tipo, identificacion, empresa_operadora, estado)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (vehiculo.tipo, vehiculo.identificacion, vehiculo.empresa_operadora, vehiculo.estado),
                )
                return cursor.lastrowid
        except MySQLError as e:
            if e.errno == _MYSQL_DUPLICATE_ENTRY:
                logger.warning("Alta de vehículo duplicada: %s", e)
                raise DuplicateError(
                    f"Ya existe un vehículo con la identificación {vehiculo.identificacion}."
                ) from e
            logger.exception("Error creando vehículo")
            raise RepositoryError(f"No se pudo crear el vehículo: {e}") from e

    def obtener_por_id(self, id_vehiculo: int) -> Vehiculo | None:
        try:
            with get_cursor() as cursor:
                cursor.execute("SELECT * FROM vehiculo WHERE id_vehiculo = %s", (id_vehiculo,))
                row = cursor.fetchone()
                return _row_to_vehiculo(row) if row else None
        except MySQLError as e:
            logger.exception("Error obteniendo vehículo por id")
            raise RepositoryError(f"No se pudo obtener el vehículo: {e}") from e

    def listar(self) -> list[Vehiculo]:
        try:
            with get_cursor() as cursor:
                cursor.execute("SELECT * FROM vehiculo ORDER BY identificacion")
                return [_row_to_vehiculo(row) for row in cursor.fetchall()]
        except MySQLError as e:
            logger.exception("Error listando vehículos")
            raise RepositoryError(f"No se pudo listar los vehículos: {e}") from e

    def actualizar(self, vehiculo: Vehiculo) -> None:
        try:
            with transaction() as cursor:
                cursor.execute(
                    """
                    UPDATE vehiculo
                    SET tipo = %s, identificacion = %s, empresa_operadora = %s, estado = %s
                    WHERE id_vehiculo = %s
                    """,
                    (
                        vehiculo.tipo,
                        vehiculo.identificacion,
                        vehiculo.empresa_operadora,
                        vehiculo.estado,
                        vehiculo.id_vehiculo,
                    ),
                )
        except MySQLError as e:
            if e.errno == _MYSQL_DUPLICATE_ENTRY:
                logger.warning("Actualización de vehículo duplicada: %s", e)
                raise DuplicateError(
                    f"Ya existe otro vehículo con la identificación {vehiculo.identificacion}."
                ) from e
            logger.exception("Error actualizando vehículo")
            raise RepositoryError(f"No se pudo actualizar el vehículo: {e}") from e

    def eliminar(self, id_vehiculo: int) -> None:
        """Baja física: Vehiculo no tiene FK entrante en MySQL (se referencia
        desde Neo4j, no implementado todavía)."""
        try:
            with transaction() as cursor:
                cursor.execute("DELETE FROM vehiculo WHERE id_vehiculo = %s", (id_vehiculo,))
        except MySQLError as e:
            logger.exception("Error eliminando vehículo")
            raise RepositoryError(f"No se pudo eliminar el vehículo: {e}") from e
