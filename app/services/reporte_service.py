from app.core.exceptions import NotFoundError, ValidationError
from app.domain.reporte import Reporte
from app.repositories.reporte_repository import ReporteRepository
from app.repositories.usuario_repository import UsuarioRepository

_FORMATOS_VALIDOS = {"pdf", "csv", "xlsx"}


class ReporteService:
    def __init__(
        self,
        repository: ReporteRepository | None = None,
        usuario_repository: UsuarioRepository | None = None,
    ):
        self._repo = repository or ReporteRepository()
        self._usuario_repo = usuario_repository or UsuarioRepository()

    def generar(self, reporte: Reporte) -> Reporte:
        if not reporte.tipo or not reporte.tipo.strip():
            raise ValidationError("El tipo de reporte no puede estar vacío.")
        if reporte.formato not in _FORMATOS_VALIDOS:
            raise ValidationError(f"Formato inválido. Opciones: {', '.join(sorted(_FORMATOS_VALIDOS))}.")
        if self._usuario_repo.obtener_por_id(reporte.id_usuario) is None:
            raise ValidationError(f"No existe el usuario con id {reporte.id_usuario}.")
        id_reporte = self._repo.crear(reporte)
        reporte.id_reporte = id_reporte
        return reporte

    def eliminar(self, id_reporte: int) -> None:
        if self._repo.obtener_por_id(id_reporte) is None:
            raise NotFoundError(f"No existe un reporte con id {id_reporte}.")
        self._repo.eliminar(id_reporte)

    def obtener_por_id(self, id_reporte: int) -> Reporte:
        reporte = self._repo.obtener_por_id(id_reporte)
        if reporte is None:
            raise NotFoundError(f"No existe un reporte con id {id_reporte}.")
        return reporte

    def listar(self) -> list[Reporte]:
        return self._repo.listar()

    def listar_por_usuario(self, id_usuario: int) -> list[Reporte]:
        if self._usuario_repo.obtener_por_id(id_usuario) is None:
            raise ValidationError(f"No existe el usuario con id {id_usuario}.")
        return self._repo.listar_por_usuario(id_usuario)
