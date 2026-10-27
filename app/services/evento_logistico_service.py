from app.core.exceptions import NotFoundError, ValidationError
from app.domain.evento_logistico import EventoLogistico
from app.repositories.envio_repository import EnvioRepository
from app.repositories.evento_logistico_repository import EventoLogisticoRepository


class EventoLogisticoService:
    def __init__(
        self,
        repository: EventoLogisticoRepository | None = None,
        envio_repository: EnvioRepository | None = None,
    ):
        self._repo = repository or EventoLogisticoRepository()
        self._envio_repo = envio_repository or EnvioRepository()

    def registrar(self, evento: EventoLogistico) -> EventoLogistico:
        if not evento.tipo_evento or not evento.tipo_evento.strip():
            raise ValidationError("El tipo de evento no puede estar vacío.")
        if self._envio_repo.obtener_por_id(evento.id_envio) is None:
            raise ValidationError(f"No existe el envío con id {evento.id_envio}.")
        id_evento = self._repo.crear(evento)
        evento.id_evento = id_evento
        return evento

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
