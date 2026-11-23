"""Reglas de negocio de LecturaSensor. Implementa el pipeline de eventos en
una sola dirección que describe el desafío de complejidad adicional:
Cassandra (lectura anómala) -> MongoDB (Incidente) -> Redis (Alerta). El
tramo Incidente+Alerta es una transacción cross-engine con rollback manual
(ver _registrar_incidente_y_alerta_transaccional): si la Alerta en Redis
falla después de confirmado el Incidente en Mongo, el Incidente se deshace
en vez de quedar huérfano. Aun así, el pipeline completo nunca hace fallar
el registro de la lectura: si esa transacción falla (ya revertida) o falla
la evaluación de reglas, se loguea y se sigue — la lectura en Cassandra ya
quedó guardada, que es lo único que no puede perderse."""
import logging
from datetime import datetime

from app.core.exceptions import AppError, RepositoryError, TransaccionCrossEngineError, ValidationError
from app.domain.incidente import Incidente
from app.domain.lectura_sensor import CAMPO_POR_TIPO_SENSOR, LecturaSensor
from app.repositories.contenedor_repository import ContenedorRepository
from app.repositories.envio_contenedor_repository import EnvioContenedorRepository
from app.repositories.lectura_sensor_repository import LecturaSensorRepository
from app.repositories.regla_repository import ReglaRepository
from app.repositories.sensor_iot_repository import SensorIoTRepository
from app.services.alerta_service import AlertaService
from app.services.incidente_service import IncidenteService

logger = logging.getLogger(__name__)

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
        contenedor_repository: ContenedorRepository | None = None,
    ):
        self._repo = repository or LecturaSensorRepository()
        self._sensor_repo = sensor_repository or SensorIoTRepository()
        self._regla_repo = regla_repository or ReglaRepository()
        self._envio_contenedor_repo = envio_contenedor_repository or EnvioContenedorRepository()
        self._incidente_service = incidente_service or IncidenteService()
        self._alerta_service = alerta_service or AlertaService()
        self._contenedor_repo = contenedor_repository or ContenedorRepository()

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

    def listar_por_contenedor(self, id_contenedor: int, limite: int = 200) -> list[LecturaSensor]:
        """Reconstruye el recorrido de un contenedor combinando las lecturas
        de TODOS sus sensores (no de uno en particular), ordenadas por
        fecha_hora — lo que separadamente expone LecturaSensorRepository por
        id_sensor (su partition key en Cassandra) no alcanza para "el
        recorrido del contenedor" si tiene más de un sensor."""
        if self._contenedor_repo.obtener_por_id(id_contenedor) is None:
            raise ValidationError(f"No existe el contenedor con id {id_contenedor}.")
        lecturas = []
        for sensor in self._sensor_repo.listar_por_contenedor(id_contenedor):
            lecturas.extend(self._repo.listar_por_sensor(sensor.id_sensor, limite=limite))
        lecturas.sort(key=lambda l: l.fecha_hora)
        return lecturas

    def _evaluar_reglas(self, sensor, lectura: LecturaSensor) -> None:
        reglas = self._regla_repo.listar_por_tipo_sensor(sensor.tipo)
        for regla in reglas:
            campo = CAMPO_POR_TIPO_SENSOR.get(regla.tipo_sensor)
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

        if id_envio is None:
            # Sin envío asignado no hay nada a lo que vincular un Incidente,
            # así que la Alerta se genera sola — no participa de la
            # transacción Incidente+Alerta de más abajo.
            logger.warning(
                "El contenedor %s no tiene envío asignado: se genera la alerta sin incidente vinculado",
                sensor.id_contenedor,
            )
            try:
                self._alerta_service.generar_alerta(sensor.id_sensor, regla.id_regla, id_evento=None)
            except AppError:
                logger.exception("No se pudo generar la alerta derivada de la lectura")
            return

        try:
            self._registrar_incidente_y_alerta_transaccional(sensor, regla, id_envio)
        except AppError:
            # Igual que el resto del pipeline: se loguea y se sigue, la
            # lectura en Cassandra ya quedó guardada y es lo único que no
            # puede perderse por esto.
            logger.exception("Transacción incidente+alerta fallida para la lectura del sensor %s", sensor.id_sensor)

    def _registrar_incidente_y_alerta_transaccional(self, sensor, regla, id_envio: int) -> None:
        """Transacción Incidente(Mongo) + Alerta(Redis) con rollback manual:
        no hay 2PC posible entre motores heterogéneos, así que la atomicidad
        se logra a mano — se confirma el Incidente primero (motor 'fuente'
        de este par) y si la Alerta no puede generarse, se deshace
        (compensación) el Incidente recién creado en vez de dejarlo huérfano
        sin alerta asociada."""
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
        try:
            self._alerta_service.generar_alerta(
                sensor.id_sensor, regla.id_regla, id_evento=incidente.id_incidente
            )
        except AppError as e:
            logger.exception(
                "No se pudo generar la alerta del incidente %s: se revierte el incidente (rollback)",
                incidente.id_incidente,
            )
            self._incidente_service.eliminar(incidente.id_incidente)
            raise TransaccionCrossEngineError(
                f"Falló la alerta del incidente {incidente.id_incidente} en Redis; "
                "el incidente en Mongo fue revertido."
            ) from e
