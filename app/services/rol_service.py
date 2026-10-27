from app.core.exceptions import NotFoundError, ValidationError
from app.domain.rol import Rol
from app.repositories.rol_repository import RolRepository


class RolService:
    def __init__(self, repository: RolRepository | None = None):
        self._repo = repository or RolRepository()

    def _validar(self, rol: Rol) -> None:
        if not rol.descripcion or not rol.descripcion.strip():
            raise ValidationError("La descripción no puede estar vacía.")
        if rol.nivel_permisos < 0:
            raise ValidationError("El nivel de permisos no puede ser negativo.")

    def dar_alta(self, rol: Rol) -> Rol:
        self._validar(rol)
        id_rol = self._repo.crear(rol)
        rol.id_rol = id_rol
        return rol

    def modificar(self, rol: Rol) -> None:
        if rol.id_rol is None:
            raise ValidationError("No se puede modificar un rol sin id_rol.")
        self._validar(rol)
        if self._repo.obtener_por_id(rol.id_rol) is None:
            raise NotFoundError(f"No existe un rol con id {rol.id_rol}.")
        self._repo.actualizar(rol)

    def eliminar(self, id_rol: int) -> None:
        if self._repo.obtener_por_id(id_rol) is None:
            raise NotFoundError(f"No existe un rol con id {id_rol}.")
        self._repo.eliminar(id_rol)

    def obtener_por_id(self, id_rol: int) -> Rol:
        rol = self._repo.obtener_por_id(id_rol)
        if rol is None:
            raise NotFoundError(f"No existe un rol con id {id_rol}.")
        return rol

    def listar(self) -> list[Rol]:
        return self._repo.listar()
