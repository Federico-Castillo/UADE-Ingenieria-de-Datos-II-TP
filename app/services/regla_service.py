from app.core.exceptions import NotFoundError, ValidationError
from app.domain.regla import Regla
from app.repositories.regla_repository import ReglaRepository
from app.repositories.usuario_repository import UsuarioRepository

_OPERADORES_VALIDOS = {">", ">=", "<", "<=", "="}
_SEVERIDADES_VALIDAS = {"baja", "media", "alta", "critica"}


class ReglaService:
    def __init__(
        self,
        repository: ReglaRepository | None = None,
        usuario_repository: UsuarioRepository | None = None,
    ):
        self._repo = repository or ReglaRepository()
        self._usuario_repo = usuario_repository or UsuarioRepository()

    def _validar(self, regla: Regla) -> None:
        if not regla.nombre or not regla.nombre.strip():
            raise ValidationError("El nombre no puede estar vacío.")
        if not regla.tipo_sensor or not regla.tipo_sensor.strip():
            raise ValidationError("El tipo de sensor no puede estar vacío.")
        if regla.operador_comparacion not in _OPERADORES_VALIDOS:
            raise ValidationError(f"Operador inválido. Opciones: {', '.join(sorted(_OPERADORES_VALIDOS))}.")
        if regla.severidad not in _SEVERIDADES_VALIDAS:
            raise ValidationError(f"Severidad inválida. Opciones: {', '.join(sorted(_SEVERIDADES_VALIDAS))}.")
        if self._usuario_repo.obtener_por_id(regla.id_usuario_creador) is None:
            raise ValidationError(f"No existe el usuario con id {regla.id_usuario_creador}.")

    def dar_alta(self, regla: Regla) -> Regla:
        self._validar(regla)
        id_regla = self._repo.crear(regla)
        regla.id_regla = id_regla
        return regla

    def modificar(self, regla: Regla) -> None:
        if regla.id_regla is None:
            raise ValidationError("No se puede modificar una regla sin id_regla.")
        self._validar(regla)
        if self._repo.obtener_por_id(regla.id_regla) is None:
            raise NotFoundError(f"No existe una regla con id {regla.id_regla}.")
        self._repo.actualizar(regla)

    def eliminar(self, id_regla: int) -> None:
        if self._repo.obtener_por_id(id_regla) is None:
            raise NotFoundError(f"No existe una regla con id {id_regla}.")
        self._repo.eliminar(id_regla)

    def obtener_por_id(self, id_regla: int) -> Regla:
        regla = self._repo.obtener_por_id(id_regla)
        if regla is None:
            raise NotFoundError(f"No existe una regla con id {id_regla}.")
        return regla

    def listar(self, solo_activas: bool = False) -> list[Regla]:
        return self._repo.listar(solo_activas=solo_activas)
