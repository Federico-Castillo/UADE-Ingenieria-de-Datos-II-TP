"""Acceso a datos de la relación N:M EnvioContenedor contra MySQL (tabla
envio_contenedor). Resuelve "ABM de contenedores de un envío" del checklist
de promoción, y es el vínculo que permite ir de un sensor -> contenedor ->
envío para el pipeline de detección de incidentes desde Cassandra."""
import logging

from mysql.connector import Error as MySQLError

from app.core.exceptions import DuplicateError, RepositoryError
from app.db.mysql import get_cursor, transaction
from app.domain.contenedor import Contenedor

logger = logging.getLogger(__name__)

_MYSQL_DUPLICATE_ENTRY = 1062


def _row_to_contenedor(row: dict) -> Contenedor:
    return Contenedor(
        id_contenedor=row["id_contenedor"],
        codigo_internacional=row["codigo_internacional"],
        tipo=row["tipo"],
        capacidad=float(row["capacidad"]),
        estado=row["estado"],
    )


class EnvioContenedorRepository:
    def asignar(self, id_envio: int, id_contenedor: int) -> None:
        try:
            with transaction() as cursor:
                cursor.execute(
                    "INSERT INTO envio_contenedor (id_envio, id_contenedor) VALUES (%s, %s)",
                    (id_envio, id_contenedor),
                )
            logger.info("Contenedor asignado id_envio=%s id_contenedor=%s", id_envio, id_contenedor)
        except MySQLError as e:
            if e.errno == _MYSQL_DUPLICATE_ENTRY:
                logger.warning("Asignación de contenedor duplicada: %s", e)
                raise DuplicateError(
                    f"El contenedor {id_contenedor} ya está asignado al envío {id_envio}."
                ) from e
            logger.exception("Error asignando contenedor a envío")
            raise RepositoryError(f"No se pudo asignar el contenedor al envío: {e}") from e

    def quitar(self, id_envio: int, id_contenedor: int) -> bool:
        try:
            with transaction() as cursor:
                cursor.execute(
                    "DELETE FROM envio_contenedor WHERE id_envio = %s AND id_contenedor = %s",
                    (id_envio, id_contenedor),
                )
                quitado = cursor.rowcount > 0
                if quitado:
                    logger.info("Contenedor quitado id_envio=%s id_contenedor=%s", id_envio, id_contenedor)
                return quitado
        except MySQLError as e:
            logger.exception("Error quitando contenedor de envío")
            raise RepositoryError(f"No se pudo quitar el contenedor del envío: {e}") from e

    def listar_contenedores_de_envio(self, id_envio: int) -> list[Contenedor]:
        try:
            with get_cursor() as cursor:
                cursor.execute(
                    """
                    SELECT c.* FROM contenedor c
                    JOIN envio_contenedor ec ON ec.id_contenedor = c.id_contenedor
                    WHERE ec.id_envio = %s
                    ORDER BY ec.fecha_asignacion
                    """,
                    (id_envio,),
                )
                return [_row_to_contenedor(row) for row in cursor.fetchall()]
        except MySQLError as e:
            logger.exception("Error listando contenedores de un envío")
            raise RepositoryError(f"No se pudo listar los contenedores del envío: {e}") from e

    def volumen_transportado_por_cliente(self) -> list[dict]:
        """Usado por el ranking "clientes por volumen transportado": suma la
        capacidad de todos los contenedores que cada cliente movió alguna vez
        (vía cualquiera de sus envíos), de mayor a menor. Es una agregación
        100% MySQL (envio_contenedor + envio + contenedor), no necesita
        resolver nada cross-engine."""
        try:
            with get_cursor() as cursor:
                cursor.execute(
                    """
                    SELECT e.id_cliente AS id_cliente,
                           SUM(c.capacidad) AS volumen_total,
                           COUNT(*) AS cantidad_contenedores
                    FROM envio_contenedor ec
                    JOIN envio e ON e.id_envio = ec.id_envio
                    JOIN contenedor c ON c.id_contenedor = ec.id_contenedor
                    GROUP BY e.id_cliente
                    ORDER BY volumen_total DESC
                    """
                )
                return [
                    {
                        "id_cliente": row["id_cliente"],
                        "volumen_total": float(row["volumen_total"]),
                        "cantidad_contenedores": row["cantidad_contenedores"],
                    }
                    for row in cursor.fetchall()
                ]
        except MySQLError as e:
            logger.exception("Error calculando el volumen transportado por cliente")
            raise RepositoryError(f"No se pudo calcular el volumen transportado por cliente: {e}") from e

    def envio_actual_de_contenedor(self, id_contenedor: int) -> int | None:
        """Devuelve el id_envio asignado más recientemente a ese contenedor
        (un contenedor puede reutilizarse en envíos distintos con el tiempo)."""
        try:
            with get_cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id_envio FROM envio_contenedor
                    WHERE id_contenedor = %s
                    ORDER BY fecha_asignacion DESC
                    LIMIT 1
                    """,
                    (id_contenedor,),
                )
                row = cursor.fetchone()
                return row["id_envio"] if row else None
        except MySQLError as e:
            logger.exception("Error obteniendo el envío actual de un contenedor")
            raise RepositoryError(f"No se pudo obtener el envío del contenedor: {e}") from e
