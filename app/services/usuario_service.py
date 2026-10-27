"""Reglas de negocio de Usuario: valida datos, hashea contraseñas (nunca se
persiste ni se expone texto plano) y valida que id_rol/id_cliente existan."""
import re

from app.core.exceptions import NotFoundError, ValidationError
from app.core.security import hash_password, verify_password
from app.domain.usuario import Usuario
from app.repositories.cliente_repository import ClienteRepository
from app.repositories.rol_repository import RolRepository
from app.repositories.usuario_repository import UsuarioRepository

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class UsuarioService:
    def __init__(
        self,
        repository: UsuarioRepository | None = None,
        rol_repository: RolRepository | None = None,
        cliente_repository: ClienteRepository | None = None,
    ):
        self._repo = repository or UsuarioRepository()
        self._rol_repo = rol_repository or RolRepository()
        self._cliente_repo = cliente_repository or ClienteRepository()

    def _validar_datos(self, usuario: Usuario) -> None:
        if not usuario.nombre or not usuario.nombre.strip():
            raise ValidationError("El nombre no puede estar vacío.")
        if not usuario.apellido or not usuario.apellido.strip():
            raise ValidationError("El apellido no puede estar vacío.")
        if not _EMAIL_RE.match(usuario.email or ""):
            raise ValidationError("El email no tiene un formato válido.")
        if self._rol_repo.obtener_por_id(usuario.id_rol) is None:
            raise ValidationError(f"No existe el rol con id {usuario.id_rol}.")
        if usuario.id_cliente is not None and self._cliente_repo.obtener_por_id(usuario.id_cliente) is None:
            raise ValidationError(f"No existe el cliente con id {usuario.id_cliente}.")

    def _validar_password(self, password: str) -> None:
        if not password or len(password) < 6:
            raise ValidationError("La contraseña debe tener al menos 6 caracteres.")

    def dar_alta(self, usuario: Usuario, password: str) -> Usuario:
        self._validar_datos(usuario)
        self._validar_password(password)
        if self._repo.obtener_por_email(usuario.email) is not None:
            raise ValidationError(f"Ya existe un usuario con el email {usuario.email}.")
        usuario.password_hash = hash_password(password)
        id_usuario = self._repo.crear(usuario)
        usuario.id_usuario = id_usuario
        return usuario

    def modificar(self, usuario: Usuario) -> None:
        if usuario.id_usuario is None:
            raise ValidationError("No se puede modificar un usuario sin id_usuario.")
        self._validar_datos(usuario)
        existente = self._repo.obtener_por_id(usuario.id_usuario)
        if existente is None:
            raise NotFoundError(f"No existe un usuario con id {usuario.id_usuario}.")
        usuario.password_hash = existente.password_hash  # la contraseña se cambia aparte
        self._repo.actualizar(usuario)

    def cambiar_password(self, id_usuario: int, nueva_password: str) -> None:
        usuario = self.obtener_por_id(id_usuario)
        self._validar_password(nueva_password)
        usuario.password_hash = hash_password(nueva_password)
        self._repo.actualizar(usuario)

    def autenticar(self, email: str, password: str) -> Usuario:
        usuario = self._repo.obtener_por_email(email)
        if usuario is None or not verify_password(password, usuario.password_hash):
            raise ValidationError("Email o contraseña inválidos.")
        if usuario.estado != "activo":
            raise ValidationError("El usuario no está activo.")
        return usuario

    def dar_baja(self, id_usuario: int) -> None:
        if self._repo.obtener_por_id(id_usuario) is None:
            raise NotFoundError(f"No existe un usuario con id {id_usuario}.")
        self._repo.eliminar(id_usuario)

    def obtener_por_id(self, id_usuario: int) -> Usuario:
        usuario = self._repo.obtener_por_id(id_usuario)
        if usuario is None:
            raise NotFoundError(f"No existe un usuario con id {id_usuario}.")
        return usuario

    def listar(self, solo_activos: bool = False) -> list[Usuario]:
        return self._repo.listar(solo_activos=solo_activos)

    def buscar(self, texto: str) -> list[Usuario]:
        if not texto or not texto.strip():
            raise ValidationError("El texto de búsqueda no puede estar vacío.")
        return self._repo.buscar(texto)
