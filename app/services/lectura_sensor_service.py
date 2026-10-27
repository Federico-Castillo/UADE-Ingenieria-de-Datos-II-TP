"""Reglas de negocio de LecturaSensor. Implementa el pipeline de eventos en
una sola dirección que describe el desafío de complejidad adicional:
Cassandra (lectura anómala) -> MongoDB (Incidente) -> Redis (Alerta). El
pipeline nunca hace fallar el registro de la lectura: si algo falla al
evaluar reglas o disparar incidente/alerta, se loguea y se sigue — la lectura
en Cassandra ya quedó guardada, que es lo único que no puede perderse."""
import logging
from datetime import datetime

from app.core.exceptions import AppError, RepositoryError, ValidationError
from app.domain.incidente import Incidente
from app.domain.lectura_sensor import LecturaSensor
from app.repositories.envio_contenedor_repository import EnvioContenedorRepository
from app.repositories.lectura_sensor_repository import LecturaSensorRepository
from app.repositories.regla_repository import ReglaRepository
from app.repositories.sensor_iot_repository import SensorIoTRepository
from app.services.alerta_service import AlertaService
from app.services.incidente_service import IncidenteService

logger = logging.getLogger(__name__)

_CAMPO_POR_TIPO_SENSOR = {
    "temperatura": "temperatura",
    "humedad": "humedad",
    "vibracion": "vibracion",
    "bateria": "nivel_bateria",
}

_COMPARADORES = {
    ">": lambda v, u: v > u,
    ">=": lambda v, u: v >= u,
    "<": lambda v, u: v < u,
    "<=": lambda v, u: v <= u,
    "=": lambda v, u: v == u,
}


class LecturaSensorService:
    def __init__(
        self,
        repository: LecturaSensorRepository | None = None,
        sensor_repository: SensorIoTRepository | None = None,
        regla_repository: ReglaRepository | None = None,
        envio_contenedor_repository: EnvioContenedorRepository | None = None,
        incidente_service: IncidenteService | None = None,
        alerta_service: AlertaService | None = None,
    ):
        self._repo = repository or LecturaSensorRepository()
        self._sensor_repo = sensor_repository or SensorIoTRepository()
        self._regla_repo = regla_repository or ReglaRepository()
        self._envio_contenedor_repo = envio_contenedor_repository or EnvioContenedorRepository()
        self._incidente_service = incidente_service or IncidenteService()
        self._alerta_service = alerta_service or AlertaService()

    def registrar_lectura(self, lectura: LecturaSensor) -> LecturaSensor:
        sensor = self._sensor_repo.obtener_por_id(lectura.id_sensor)
        if sensor is None:
            raise ValidationError(f"No existe el sensor con id {lectura.id_sensor}.")

        lectura = self._repo.crear(lectura)

        try:
            self._evaluar_reglas(sensor, lectura)
        except Exception:
            logger.exception("Fallo evaluando reglas para la lectura %s", lectura.id_lectura)

        return lectura

    def listar_por_sensor(self, id_sensor: int, limite: int = 50) -> list[LecturaSensor]:
        if self._sensor_repo.obtener_por_id(id_sensor) is None:
            raise ValidationError(f"No existe el sensor con id {id_sensor}.")
        return self._repo.listar_por_sensor(id_sensor, limite=limite)

    def listar_por_rango(self, id_sensor: int, desde: datetime, hasta: datetime) -> list[LecturaSensor]:
        if self._sensor_repo.obtener_por_id(id_sensor) is None:
            raise ValidationError(f"No existe el sensor con id {id_sensor}.")
        return self._repo.listar_por_rango(id_sensor, desde, hasta)

    def ultima_por_sensor(self, id_sensor: int) -> LecturaSensor | None:
        if self._sensor_repo.obtener_por_id(id_sensor) is None:
            raise ValidationError(f"No existe el sensor con id {id_sensor}.")
        return self._repo.ultima_por_sensor(id_sensor)

    def _evaluar_reglas(self, sensor, lectura: LecturaSensor) -> None:
        reglas = self._regla_repo.listar_por_tipo_sensor(sensor.tipo)
        for regla in reglas:
            campo = _CAMPO_POR_TIPO_SENSOR.get(regla.tipo_sensor)
            valor = getattr(lectura, campo, None) if campo else None
            if valor is None:
                continue
            comparador = _COMPARADORES.get(regla.operador_comparacion)
            if comparador and comparador(valor, regla.valor_umbral):
                self._disparar_incidente_y_alerta(sensor, regla)

    def _disparar_incidente_y_alerta(self, sensor, regla) -> None:
        id_envio = None
        try:
            id_envio = self._envio_contenedor_repo.envio_actual_de_contenedor(sensor.id_contenedor)
        except RepositoryError:
            logger.exception("No se pudo resolver el envío del contenedor %s", sensor.id_contenedor)

        id_evento = None
        if id_envio is not None:
            try:
                incidente = self._incidente_service.registrar(
                    Incidente(
                        id_envio=id_envio,
                        tipo=f"anomalia_{regla.tipo_sensor}",
                        severidad=regla.severidad,
                        descripcion=(
                            f"Lectura del sensor {sensor.id_sensor} violó la regla '{regla.nombre}' "
                            f"({regla.tipo_sensor} {regla.operador_comparacion} {regla.valor_umbral})."
                        ),
                    )
                )
                id_evento = incidente.id_incidente
            except AppError:
                logger.exception("No se pudo registrar el incidente derivado de la lectura")
        else:
            logger.warning(
                "El contenedor %s no tiene envío asignado: se genera la alerta sin incidente vinculado",
                sensor.id_contenedor,
            )

        try:
            self._alerta_service.generar_alerta(sensor.id_sensor, regla.id_regla, id_evento=id_evento)
        except AppError:
            logger.exception("No se pudo generar la alerta derivada de la lectura")
