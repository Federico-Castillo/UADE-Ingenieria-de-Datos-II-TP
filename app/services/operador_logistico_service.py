"""Reglas de negocio de OperadorLogistico. Mismo criterio que Cliente/Proveedor."""
import re

from app.core.exceptions import NotFoundError, ValidationError
from app.domain.operador_logistico import OperadorLogistico
from app.repositories.operador_logistico_repository import OperadorLogisticoRepository

_CUIT_RE = re.compile(r"^\d{2}-\d{8}-\d{1}$")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class OperadorLogisticoService:
    def __init__(self, repository: OperadorLogisticoRepository | None = None):
        self._repo = repository or OperadorLogisticoRepository()

    def _validar(self, operador: OperadorLogistico) -> None:
        if not operador.razon_social or not operador.razon_social.strip():
            raise ValidationError("La razón social no puede estar vacía.")
        if not _CUIT_RE.match(operador.cuit or ""):
            raise ValidationError("El CUIT debe tener el formato XX-XXXXXXXX-X.")
        if not _EMAIL_RE.match(operador.email or ""):
            raise ValidationError("El email no tiene un formato válido.")

    def dar_alta(self, operador: OperadorLogistico) -> OperadorLogistico:
        self._validar(operador)
        if self._repo.obtener_por_cuit(operador.cuit) is not None:
            raise ValidationError(f"Ya existe un operador logístico con el CUIT {operador.cuit}.")
        if self._repo.obtener_por_email(operador.email) is not None:
            raise ValidationError(f"Ya existe un operador logístico con el email {operador.email}.")
        id_operador = self._repo.crear(operador)
        operador.id_operador_logistico = id_operador
        return operador

    def modificar(self, operador: OperadorLogistico) -> None:
        if operador.id_operador_logistico is None:
            raise ValidationError("No se puede modificar un operador logístico sin id.")
        self._validar(operador)
        if self._repo.obtener_por_id(operador.id_operador_logistico) is None:
            raise NotFoundError(f"No existe un operador logístico con id {operador.id_operador_logistico}.")
        self._repo.actualizar(operador)

    def dar_baja(self, id_operador_logistico: int) -> None:
        if self._repo.obtener_por_id(id_operador_logistico) is None:
            raise NotFoundError(f"No existe un operador logístico con id {id_operador_logistico}.")
        self._repo.eliminar(id_operador_logistico)

    def obtener_por_id(self, id_operador_logistico: int) -> OperadorLogistico:
        operador = self._repo.obtener_por_id(id_operador_logistico)
        if operador is None:
            raise NotFoundError(f"No existe un operador logístico con id {id_operador_logistico}.")
        return operador

    def listar(self, solo_activos: bool = False) -> list[OperadorLogistico]:
        return self._repo.listar(solo_activos=solo_activos)

    def buscar(self, texto: str) -> list[OperadorLogistico]:
        if not texto or not texto.strip():
            raise ValidationError("El texto de búsqueda no puede estar vacío.")
        return self._repo.buscar(texto)
