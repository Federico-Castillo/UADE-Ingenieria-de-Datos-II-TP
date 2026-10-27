from app.core.exceptions import ValidationError
from app.domain.contenedor import Contenedor
from app.repositories.contenedor_repository import ContenedorRepository
from app.repositories.envio_contenedor_repository import EnvioContenedorRepository
from app.repositories.envio_repository import EnvioRepository


class EnvioContenedorService:
    def __init__(
        self,
        repository: EnvioContenedorRepository | None = None,
        envio_repository: EnvioRepository | None = None,
        contenedor_repository: ContenedorRepository | None = None,
    ):
        self._repo = repository or EnvioContenedorRepository()
        self._envio_repo = envio_repository or EnvioRepository()
        self._contenedor_repo = contenedor_repository or ContenedorRepository()

    def asignar_contenedor(self, id_envio: int, id_contenedor: int) -> None:
        if self._envio_repo.obtener_por_id(id_envio) is None:
            raise ValidationError(f"No existe el envío con id {id_envio}.")
        if self._contenedor_repo.obtener_por_id(id_contenedor) is None:
            raise ValidationError(f"No existe el contenedor con id {id_contenedor}.")
        self._repo.asignar(id_envio, id_contenedor)

    def quitar_contenedor(self, id_envio: int, id_contenedor: int) -> None:
        if not self._repo.quitar(id_envio, id_contenedor):
            raise ValidationError(f"El contenedor {id_contenedor} no está asignado al envío {id_envio}.")

    def listar_contenedores_de_envio(self, id_envio: int) -> list[Contenedor]:
        if self._envio_repo.obtener_por_id(id_envio) is None:
            raise ValidationError(f"No existe el envío con id {id_envio}.")
        return self._repo.listar_contenedores_de_envio(id_envio)

    def envio_actual_de_contenedor(self, id_contenedor: int) -> int | None:
        if self._contenedor_repo.obtener_por_id(id_contenedor) is None:
            raise ValidationError(f"No existe el contenedor con id {id_contenedor}.")
        return self._repo.envio_actual_de_contenedor(id_contenedor)
