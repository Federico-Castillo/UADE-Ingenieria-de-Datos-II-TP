"""Acceso a datos de LecturaSensor contra Cassandra (tabla lecturas_sensor).
Partition key = id_sensor, clustering key = fecha_hora DESC + id_lectura, tal
cual modelado.md. id_lectura es un UUID generado en Python (Cassandra no
tiene AUTO_INCREMENT)."""
import logging
import uuid
from datetime import datetime, timezone

from app.config import get_config
from app.core.exceptions import RepositoryError
from app.db.cassandra_client import get_session  # noqa: E402 - aplica el shim de compat antes de cassandra.cluster
from app.domain.lectura_sensor import LecturaSensor

from cassandra import InvalidRequest
from cassandra.cluster import NoHostAvailable, OperationTimedOut

logger = logging.getLogger(__name__)

_INSERT = """
INSERT INTO lecturas_sensor
    (id_sensor, fecha_hora, id_lectura, temperatura, humedad, vibracion, gps_lat, gps_lon, nivel_bateria)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
"""

_SELECT_POR_SENSOR = """
SELECT id_sensor, fecha_hora, id_lectura, temperatura, humedad, vibracion, gps_lat, gps_lon, nivel_bateria
FROM lecturas_sensor WHERE id_sensor = %s LIMIT %s
"""

_SELECT_POR_RANGO = """
SELECT id_sensor, fecha_hora, id_lectura, temperatura, humedad, vibracion, gps_lat, gps_lon, nivel_bateria
FROM lecturas_sensor WHERE id_sensor = %s AND fecha_hora >= %s AND fecha_hora <= %s
"""

_SELECT_ULTIMA = """
SELECT id_sensor, fecha_hora, id_lectura, temperatura, humedad, vibracion, gps_lat, gps_lon, nivel_bateria
FROM lecturas_sensor WHERE id_sensor = %s LIMIT 1
"""

_CASSANDRA_ERRORS = (InvalidRequest, NoHostAvailable, OperationTimedOut)


def _row_to_lectura(row) -> LecturaSensor:
    return LecturaSensor(
        id_sensor=row.id_sensor,
        fecha_hora=row.fecha_hora,
        id_lectura=str(row.id_lectura),
        temperatura=row.temperatura,
        humedad=row.humedad,
        vibracion=row.vibracion,
        gps_lat=row.gps_lat,
        gps_lon=row.gps_lon,
        nivel_bateria=row.nivel_bateria,
    )


class LecturaSensorRepository:
    def __init__(self):
        self._session = get_session(keyspace=get_config().cassandra.keyspace)

    def crear(self, lectura: LecturaSensor) -> LecturaSensor:
        try:
            id_lectura = uuid.uuid4()
            fecha_hora = lectura.fecha_hora or datetime.now(timezone.utc)
            self._session.execute(
                _INSERT,
                (
                    lectura.id_sensor,
                    fecha_hora,
                    id_lectura,
                    lectura.temperatura,
                    lectura.humedad,
                    lectura.vibracion,
                    lectura.gps_lat,
                    lectura.gps_lon,
                    lectura.nivel_bateria,
                ),
            )
            lectura.id_lectura = str(id_lectura)
            lectura.fecha_hora = fecha_hora
            logger.info("Lectura de sensor creada id=%s id_sensor=%s", lectura.id_lectura, lectura.id_sensor)
            return lectura
        except _CASSANDRA_ERRORS as e:
            logger.exception("Error creando lectura de sensor")
            raise RepositoryError(f"No se pudo crear la lectura: {e}") from e

    def listar_por_sensor(self, id_sensor: int, limite: int = 50) -> list[LecturaSensor]:
        try:
            rows = self._session.execute(_SELECT_POR_SENSOR, (id_sensor, limite))
            return [_row_to_lectura(r) for r in rows]
        except _CASSANDRA_ERRORS as e:
            logger.exception("Error listando lecturas de un sensor")
            raise RepositoryError(f"No se pudo listar las lecturas: {e}") from e

    def listar_por_rango(self, id_sensor: int, desde: datetime, hasta: datetime) -> list[LecturaSensor]:
        try:
            rows = self._session.execute(_SELECT_POR_RANGO, (id_sensor, desde, hasta))
            return [_row_to_lectura(r) for r in rows]
        except _CASSANDRA_ERRORS as e:
            logger.exception("Error listando lecturas por rango")
            raise RepositoryError(f"No se pudo listar las lecturas por rango: {e}") from e

    def ultima_por_sensor(self, id_sensor: int) -> LecturaSensor | None:
        try:
            rows = self._session.execute(_SELECT_ULTIMA, (id_sensor,))
            row = rows.one()
            return _row_to_lectura(row) if row else None
        except _CASSANDRA_ERRORS as e:
            logger.exception("Error obteniendo última lectura de un sensor")
            raise RepositoryError(f"No se pudo obtener la última lectura: {e}") from e
