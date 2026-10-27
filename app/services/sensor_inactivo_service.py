"""Proceso periódico "detección de sensores inactivos": compara, para cada
sensor con estado='activo' en MySQL, la fecha de su última lectura en
Cassandra contra un umbral de horas. Un sensor sin lecturas recientes (o sin
lecturas nunca) se marca 'inactivo' en MySQL y se genera una Alerta en Redis
para que quede visible junto con las alertas de violación de Regla — aunque
acá no hay una Regla que la origine, por eso se crea con AlertaRepository
directamente (AlertaService.generar_alerta exige una Regla real, que no
aplica a este caso) y id_regla=0 como sentinel explícito de "sin regla"."""
import logging
from datetime import datetime, timedelta, timezone

from app.core.exceptions import AppError
from app.core.fechas import sin_tz
from app.domain.sensor_iot import SensorIoT
from app.repositories.alerta_repository import AlertaRepository
from app.repositories.lectura_sensor_repository import LecturaSensorRepository
from app.repositories.sensor_iot_repository import SensorIoTRepository

logger = logging.getLogger(__name__)

UMBRAL_HORAS_DEFAULT = 24.0
_ID_REGLA_SIN_REGLA = 0
_TIPO_ALERTA = "sensor_inactivo"


class SensorInactivoService:
    def __init__(
        self,
        sensor_repo: SensorIoTRepository | None = None,
        lectura_repo: LecturaSensorRepository | None = None,
        alerta_repo: AlertaRepository | None = None,
    ):
        self._sensor_repo = sensor_repo or SensorIoTRepository()
        self._lectura_repo = lectura_repo or LecturaSensorRepository()
        self._alerta_repo = alerta_repo or AlertaRepository()

    def detectar(self, umbral_horas: float = UMBRAL_HORAS_DEFAULT) -> list[SensorIoT]:
        limite = sin_tz(datetime.now(timezone.utc) - timedelta(hours=umbral_horas))
        inactivos = []
        for sensor in self._sensor_repo.listar():
            if sensor.estado != "activo":
                continue
            ultima = self._lectura_repo.ultima_por_sensor(sensor.id_sensor)
            if ultima is None or sin_tz(ultima.fecha_hora) < limite:
                inactivos.append(sensor)
        return inactivos

    def marcar_inactivos(self, umbral_horas: float = UMBRAL_HORAS_DEFAULT) -> list[SensorIoT]:
        detectados = self.detectar(umbral_horas)
        for sensor in detectados:
            sensor.estado = "inactivo"
            self._sensor_repo.actualizar(sensor)
            try:
                self._alerta_repo.crear(sensor.id_sensor, _ID_REGLA_SIN_REGLA, _TIPO_ALERTA)
            except AppError:
                logger.exception("No se pudo generar la alerta de sensor inactivo (sensor %s)", sensor.id_sensor)
        logger.info("Detección de sensores inactivos: %s sensor(es) marcados", len(detectados))
        return detectados
