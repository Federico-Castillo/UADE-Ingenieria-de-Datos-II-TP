import logging

from app.core.exceptions import AppError, NotFoundError, TransaccionCrossEngineError, ValidationError
from app.domain.evento_logistico import EventoLogistico
from app.repositories.envio_repository import EnvioRepository
from app.repositories.evento_logistico_repository import EventoLogisticoRepository

logger = logging.getLogger(__name__)

# Eventos que mueven el estado del envío: tipo_evento -> (estado nuevo, estados
# desde los que se aplica). Es una regla de un solo sentido a propósito:
#  - un envío 'cancelado' no se reactiva por un evento tardío;
#  - un envío 'demorado' que se entrega sigue 'demorado' (el modelo de
#    predicción usa 'demorado' como la etiqueta de "llegó tarde");
#  - el resto de los tipos (aduana, retraso, descarga...) es solo historial.
_TRANSICIONES = {
    "carga_iniciada": ("en_transito", {"pendiente"}),
    "salida_origen": ("en_transito", {"pendiente"}),
    "en_transito": ("en_transito", {"pendiente"}),
    "entregado": ("entregado", {"pendiente", "en_transito"}),
}


def estado_tras_evento(estado_actual: str, tipo_evento: str) -> str:
    """Estado que le corresponde al envío tras un evento (el mismo si no aplica)."""
    transicion = _TRANSICIONES.get(tipo_evento)
    if transicion is None:
        return estado_actual
    nuevo, desde = transicion
    return nuevo if estado_actual in desde else estado_actual


class EventoLogisticoService:
    def __init__(
        self,
        repository: EventoLogisticoRepository | None = None,
        envio_repository: EnvioRepository | None = None,
    ):
        self._repo = repository or EventoLogisticoRepository()
        self._envio_repo = envio_repository or EnvioRepository()

    def registrar(self, evento: EventoLogistico) -> EventoLogistico:
        """Guarda el evento (Mongo) y, si corresponde, actualiza el estado del
        envío (MySQL). No hay 2PC entre motores: si falla la actualización del
        envío se borra el evento recién creado (compensación), igual que el
        par Incidente+Alerta."""
        if not evento.tipo_evento or not evento.tipo_evento.strip():
            raise ValidationError("El tipo de evento no puede estar vacío.")
        envio = self._envio_repo.obtener_por_id(evento.id_envio)
        if envio is None:
            raise ValidationError(f"No existe el envío con id {evento.id_envio}.")
        id_evento = self._repo.crear(evento)
        evento.id_evento = id_evento

        nuevo_estado = estado_tras_evento(envio.estado, evento.tipo_evento)
        if nuevo_estado != envio.estado:
            try:
                envio.estado = nuevo_estado
                self._envio_repo.actualizar(envio)
            except AppError as e:
                logger.exception(
                    "No se pudo actualizar el estado del envío %s: se revierte el evento %s (rollback)",
                    evento.id_envio, id_evento,
                )
                self._repo.eliminar(id_evento)
                raise TransaccionCrossEngineError(
                    f"No se pudo actualizar el estado del envío {evento.id_envio} a '{nuevo_estado}'; "
                    "el evento en Mongo fue revertido."
                ) from e
            logger.info("Envío %s pasó a '%s' por el evento '%s'", evento.id_envio, nuevo_estado, evento.tipo_evento)
        return evento

    def sincronizar_estados_envios(self) -> list[dict]:
        """Reconcilia los envíos existentes con su historial: repasa los eventos
        de cada envío en orden cronológico y le aplica las mismas transiciones
        que `registrar`. Corrige estados que quedaron desfasados porque los
        eventos se cargaron antes de que existiera esta regla. Devuelve los
        envíos modificados como [{'id_envio', 'antes', 'despues'}]."""
        cambios = []
        for envio in self._envio_repo.listar():
            estado = envio.estado
            for evento in self._repo.listar_por_envio(envio.id_envio):
                estado = estado_tras_evento(estado, evento.tipo_evento)
            if estado != envio.estado:
                antes, envio.estado = envio.estado, estado
                self._envio_repo.actualizar(envio)
                cambios.append({"id_envio": envio.id_envio, "antes": antes, "despues": estado})
        return cambios

    def obtener_por_id(self, id_evento: str) -> EventoLogistico:
        evento = self._repo.obtener_por_id(id_evento)
        if evento is None:
            raise NotFoundError(f"No existe un evento con id {id_evento}.")
        return evento

    def listar_por_envio(self, id_envio: int) -> list[EventoLogistico]:
        if self._envio_repo.obtener_por_id(id_envio) is None:
            raise ValidationError(f"No existe el envío con id {id_envio}.")
        return self._repo.listar_por_envio(id_envio)

    def listar(self) -> list[EventoLogistico]:
        return self._repo.listar()
