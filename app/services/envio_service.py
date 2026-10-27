from app.core.exceptions import NotFoundError, ValidationError
from app.domain.envio import Envio
from app.repositories.cliente_repository import ClienteRepository
from app.repositories.envio_repository import EnvioRepository

_PRIORIDADES_VALIDAS = {"baja", "normal", "alta", "urgente"}


class EnvioService:
    def __init__(
        self,
        repository: EnvioRepository | None = None,
        cliente_repository: ClienteRepository | None = None,
    ):
        self._repo = repository or EnvioRepository()
        self._cliente_repo = cliente_repository or ClienteRepository()

    def _validar(self, envio: Envio) -> None:
        if not envio.origen or not envio.origen.strip():
            raise ValidationError("El origen no puede estar vacío.")
        if not envio.destino or not envio.destino.strip():
            raise ValidationError("El destino no puede estar vacío.")
        if envio.prioridad not in _PRIORIDADES_VALIDAS:
            raise ValidationError(f"Prioridad inválida. Opciones: {', '.join(sorted(_PRIORIDADES_VALIDAS))}.")
        if self._cliente_repo.obtener_por_id(envio.id_cliente) is None:
            raise ValidationError(f"No existe el cliente con id {envio.id_cliente}.")

    def dar_alta(self, envio: Envio) -> Envio:
        self._validar(envio)
        id_envio = self._repo.crear(envio)
        envio.id_envio = id_envio
        return envio

    def modificar(self, envio: Envio) -> None:
        if envio.id_envio is None:
            raise ValidationError("No se puede modificar un envío sin id_envio.")
        self._validar(envio)
        if self._repo.obtener_por_id(envio.id_envio) is None:
            raise NotFoundError(f"No existe un envío con id {envio.id_envio}.")
        self._repo.actualizar(envio)

    def eliminar(self, id_envio: int) -> None:
        if self._repo.obtener_por_id(id_envio) is None:
            raise NotFoundError(f"No existe un envío con id {id_envio}.")
        self._repo.eliminar(id_envio)

    def obtener_por_id(self, id_envio: int) -> Envio:
        envio = self._repo.obtener_por_id(id_envio)
        if envio is None:
            raise NotFoundError(f"No existe un envío con id {id_envio}.")
        return envio

    def listar(self) -> list[Envio]:
        return self._repo.listar()

    def listar_por_cliente(self, id_cliente: int) -> list[Envio]:
        if self._cliente_repo.obtener_por_id(id_cliente) is None:
            raise ValidationError(f"No existe el cliente con id {id_cliente}.")
        return self._repo.listar_por_cliente(id_cliente)
