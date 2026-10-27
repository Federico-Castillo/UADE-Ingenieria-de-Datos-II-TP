from app.core.exceptions import NotFoundError, ValidationError
from app.domain.sesion import Sesion
from app.repositories.sesion_repository import SesionRepository
from app.repositories.usuario_repository import UsuarioRepository


class SesionService:
    def __init__(
        self,
        repository: SesionRepository | None = None,
        usuario_repository: UsuarioRepository | None = None,
    ):
        self._repo = repository or SesionRepository()
        self._usuario_repo = usuario_repository or UsuarioRepository()

    def iniciar_sesion(self, id_usuario: int) -> Sesion:
        if self._usuario_repo.obtener_por_id(id_usuario) is None:
            raise ValidationError(f"No existe el usuario con id {id_usuario}.")
        return self._repo.crear(id_usuario)

    def cerrar_sesion(self, id_sesion: str) -> None:
        cerrada = self._repo.cerrar(id_sesion)
        if not cerrada:
            raise NotFoundError(f"No existe una sesión activa con id {id_sesion}.")

    def obtener(self, id_sesion: str) -> Sesion:
        sesion = self._repo.obtener(id_sesion)
        if sesion is None:
            raise NotFoundError(f"No existe una sesión activa con id {id_sesion}.")
        return sesion

    def listar_activas_de_usuario(self, id_usuario: int) -> list[Sesion]:
        return self._repo.listar_activas_de_usuario(id_usuario)

    def listar_todas_activas(self) -> list[Sesion]:
        return self._repo.listar_todas_activas()
