from app.core.exceptions import NotFoundError, ValidationError
from app.domain.incidente import Incidente
from app.repositories.envio_repository import EnvioRepository
from app.repositories.incidente_repository import IncidenteRepository

_SEVERIDADES_VALIDAS = {"baja", "media", "alta", "critica"}
_ESTADOS_VALIDOS = {"abierto", "en_revision", "cerrado"}


class IncidenteService:
    def __init__(
        self,
        repository: IncidenteRepository | None = None,
        envio_repository: EnvioRepository | None = None,
    ):
        self._repo = repository or IncidenteRepository()
        self._envio_repo = envio_repository or EnvioRepository()

    def registrar(self, incidente: Incidente) -> Incidente:
        if not incidente.tipo or not incidente.tipo.strip():
            raise ValidationError("El tipo de incidente no puede estar vacío.")
        if incidente.severidad not in _SEVERIDADES_VALIDAS:
            raise ValidationError(f"Severidad inválida. Opciones: {', '.join(sorted(_SEVERIDADES_VALIDAS))}.")
        if self._envio_repo.obtener_por_id(incidente.id_envio) is None:
            raise ValidationError(f"No existe el envío con id {incidente.id_envio}.")
        id_incidente = self._repo.crear(incidente)
        incidente.id_incidente = id_incidente
        return incidente

    def cambiar_estado(self, id_incidente: str, estado: str) -> None:
        if estado not in _ESTADOS_VALIDOS:
            raise ValidationError(f"Estado inválido. Opciones: {', '.join(sorted(_ESTADOS_VALIDOS))}.")
        actualizado = self._repo.actualizar_estado(id_incidente, estado)
        if not actualizado:
            raise NotFoundError(f"No existe un incidente con id {id_incidente}.")

    def obtener_por_id(self, id_incidente: str) -> Incidente:
        incidente = self._repo.obtener_por_id(id_incidente)
        if incidente is None:
            raise NotFoundError(f"No existe un incidente con id {id_incidente}.")
        return incidente

    def listar_por_envio(self, id_envio: int) -> list[Incidente]:
        if self._envio_repo.obtener_por_id(id_envio) is None:
            raise ValidationError(f"No existe el envío con id {id_envio}.")
        return self._repo.listar_por_envio(id_envio)

    def listar(self, solo_abiertos: bool = False) -> list[Incidente]:
        return self._repo.listar(solo_abiertos=solo_abiertos)
