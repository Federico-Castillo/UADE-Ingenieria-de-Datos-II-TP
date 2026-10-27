"""Reglas de negocio de Proveedor. Mismo criterio de validación que Cliente."""
import re

from app.core.exceptions import NotFoundError, ValidationError
from app.domain.proveedor import Proveedor
from app.repositories.proveedor_repository import ProveedorRepository

_CUIT_RE = re.compile(r"^\d{2}-\d{8}-\d{1}$")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class ProveedorService:
    def __init__(self, repository: ProveedorRepository | None = None):
        self._repo = repository or ProveedorRepository()

    def _validar(self, proveedor: Proveedor) -> None:
        if not proveedor.razon_social or not proveedor.razon_social.strip():
            raise ValidationError("La razón social no puede estar vacía.")
        if not _CUIT_RE.match(proveedor.cuit or ""):
            raise ValidationError("El CUIT debe tener el formato XX-XXXXXXXX-X.")
        if not _EMAIL_RE.match(proveedor.email or ""):
            raise ValidationError("El email no tiene un formato válido.")

    def dar_alta(self, proveedor: Proveedor) -> Proveedor:
        self._validar(proveedor)
        if self._repo.obtener_por_cuit(proveedor.cuit) is not None:
            raise ValidationError(f"Ya existe un proveedor con el CUIT {proveedor.cuit}.")
        if self._repo.obtener_por_email(proveedor.email) is not None:
            raise ValidationError(f"Ya existe un proveedor con el email {proveedor.email}.")
        id_proveedor = self._repo.crear(proveedor)
        proveedor.id_proveedor = id_proveedor
        return proveedor

    def modificar(self, proveedor: Proveedor) -> None:
        if proveedor.id_proveedor is None:
            raise ValidationError("No se puede modificar un proveedor sin id_proveedor.")
        self._validar(proveedor)
        if self._repo.obtener_por_id(proveedor.id_proveedor) is None:
            raise NotFoundError(f"No existe un proveedor con id {proveedor.id_proveedor}.")
        self._repo.actualizar(proveedor)

    def dar_baja(self, id_proveedor: int) -> None:
        if self._repo.obtener_por_id(id_proveedor) is None:
            raise NotFoundError(f"No existe un proveedor con id {id_proveedor}.")
        self._repo.eliminar(id_proveedor)

    def obtener_por_id(self, id_proveedor: int) -> Proveedor:
        proveedor = self._repo.obtener_por_id(id_proveedor)
        if proveedor is None:
            raise NotFoundError(f"No existe un proveedor con id {id_proveedor}.")
        return proveedor

    def listar(self, solo_activos: bool = False) -> list[Proveedor]:
        return self._repo.listar(solo_activos=solo_activos)

    def buscar(self, texto: str) -> list[Proveedor]:
        if not texto or not texto.strip():
            raise ValidationError("El texto de búsqueda no puede estar vacío.")
        return self._repo.buscar(texto)
