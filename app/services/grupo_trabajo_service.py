from app.core.exceptions import NotFoundError, ValidationError
from app.domain.grupo_trabajo import GrupoTrabajo
from app.repositories.grupo_trabajo_repository import GrupoTrabajoRepository
from app.repositories.usuario_repository import UsuarioRepository


class GrupoTrabajoService:
    def __init__(
        self,
        repository: GrupoTrabajoRepository | None = None,
        usuario_repository: UsuarioRepository | None = None,
    ):
        self._repo = repository or GrupoTrabajoRepository()
        self._usuario_repo = usuario_repository or UsuarioRepository()

    def _validar_integrantes(self, integrantes: list[int]) -> None:
        for id_usuario in integrantes:
            if self._usuario_repo.obtener_por_id(id_usuario) is None:
                raise ValidationError(f"No existe el usuario con id {id_usuario}.")

    def crear(self, grupo: GrupoTrabajo) -> GrupoTrabajo:
        if not grupo.nombre or not grupo.nombre.strip():
            raise ValidationError("El nombre del grupo no puede estar vacío.")
        self._validar_integrantes(grupo.integrantes)
        id_grupo = self._repo.crear(grupo)
        grupo.id_grupo = id_grupo
        return grupo

    def agregar_integrante(self, id_grupo: str, id_usuario: int) -> None:
        if self._usuario_repo.obtener_por_id(id_usuario) is None:
            raise ValidationError(f"No existe el usuario con id {id_usuario}.")
        if not self._repo.agregar_integrante(id_grupo, id_usuario):
            raise NotFoundError(f"No existe un grupo con id {id_grupo}.")

    def quitar_integrante(self, id_grupo: str, id_usuario: int) -> None:
        if not self._repo.quitar_integrante(id_grupo, id_usuario):
            raise NotFoundError(f"No existe un grupo con id {id_grupo}.")

    def eliminar(self, id_grupo: str) -> None:
        if not self._repo.eliminar(id_grupo):
            raise NotFoundError(f"No existe un grupo con id {id_grupo}.")

    def obtener_por_id(self, id_grupo: str) -> GrupoTrabajo:
        grupo = self._repo.obtener_por_id(id_grupo)
        if grupo is None:
            raise NotFoundError(f"No existe un grupo con id {id_grupo}.")
        return grupo

    def listar(self) -> list[GrupoTrabajo]:
        return self._repo.listar()
