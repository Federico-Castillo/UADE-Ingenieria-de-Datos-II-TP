from app.core.exceptions import ValidationError
from app.domain.prediccion_riesgo import PrediccionRiesgo
from app.repositories.envio_repository import EnvioRepository
from app.repositories.prediccion_riesgo_repository import PrediccionRiesgoRepository


class PrediccionRiesgoService:
    def __init__(
        self,
        repository: PrediccionRiesgoRepository | None = None,
        envio_repository: EnvioRepository | None = None,
    ):
        self._repo = repository or PrediccionRiesgoRepository()
        self._envio_repo = envio_repository or EnvioRepository()

    def registrar(self, prediccion: PrediccionRiesgo) -> PrediccionRiesgo:
        if not (0.0 <= prediccion.probabilidad_demora <= 1.0):
            raise ValidationError("La probabilidad de demora debe estar entre 0 y 1.")
        if self._envio_repo.obtener_por_id(prediccion.id_envio) is None:
            raise ValidationError(f"No existe el envío con id {prediccion.id_envio}.")
        id_prediccion = self._repo.crear(prediccion)
        prediccion.id_prediccion = id_prediccion
        return prediccion

    def ultima_por_envio(self, id_envio: int) -> PrediccionRiesgo | None:
        if self._envio_repo.obtener_por_id(id_envio) is None:
            raise ValidationError(f"No existe el envío con id {id_envio}.")
        return self._repo.ultima_por_envio(id_envio)

    def listar_por_envio(self, id_envio: int) -> list[PrediccionRiesgo]:
        if self._envio_repo.obtener_por_id(id_envio) is None:
            raise ValidationError(f"No existe el envío con id {id_envio}.")
        return self._repo.listar_por_envio(id_envio)
