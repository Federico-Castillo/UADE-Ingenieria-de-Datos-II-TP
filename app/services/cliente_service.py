"""Reglas de negocio de Cliente. Nunca ve excepciones de driver — solo las que
expone ClienteRepository (RepositoryError, DuplicateError) y las propias
(ValidationError, NotFoundError)."""
import re

from app.core.exceptions import NotFoundError, ValidationError
from app.domain.cliente import Cliente
from app.repositories.cliente_repository import ClienteRepository

_CUIT_RE = re.compile(r"^\d{2}-\d{8}-\d{1}$")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class ClienteService:
    def __init__(self, repository: ClienteRepository | None = None):
        self._repo = repository or ClienteRepository()

    def _validar(self, cliente: Cliente) -> None:
        if not cliente.razon_social or not cliente.razon_social.strip():
            raise ValidationError("La razón social no puede estar vacía.")
        if not _CUIT_RE.match(cliente.cuit or ""):
            raise ValidationError("El CUIT debe tener el formato XX-XXXXXXXX-X.")
        if not _EMAIL_RE.match(cliente.email or ""):
            raise ValidationError("El email no tiene un formato válido.")

    def dar_alta(self, cliente: Cliente) -> Cliente:
        self._validar(cliente)
        # Defensa en profundidad: la DB igual tiene el UNIQUE KEY como última
        # línea, pero validar acá da un mensaje de negocio claro sin golpear la DB.
        if self._repo.obtener_por_cuit(cliente.cuit) is not None:
            raise ValidationError(f"Ya existe un cliente con el CUIT {cliente.cuit}.")
        if self._repo.obtener_por_email(cliente.email) is not None:
            raise ValidationError(f"Ya existe un cliente con el email {cliente.email}.")
        id_cliente = self._repo.crear(cliente)
        cliente.id_cliente = id_cliente
        return cliente

    def modificar(self, cliente: Cliente) -> None:
        if cliente.id_cliente is None:
            raise ValidationError("No se puede modificar un cliente sin id_cliente.")
        self._validar(cliente)
        existente = self._repo.obtener_por_id(cliente.id_cliente)
        if existente is None:
            raise NotFoundError(f"No existe un cliente con id {cliente.id_cliente}.")
        self._repo.actualizar(cliente)

    def dar_baja(self, id_cliente: int) -> None:
        existente = self._repo.obtener_por_id(id_cliente)
        if existente is None:
            raise NotFoundError(f"No existe un cliente con id {id_cliente}.")
        self._repo.eliminar(id_cliente)

    def obtener_por_id(self, id_cliente: int) -> Cliente:
        cliente = self._repo.obtener_por_id(id_cliente)
        if cliente is None:
            raise NotFoundError(f"No existe un cliente con id {id_cliente}.")
        return cliente

    def listar(self, solo_activos: bool = False) -> list[Cliente]:
        return self._repo.listar(solo_activos=solo_activos)

    def buscar(self, texto: str) -> list[Cliente]:
        if not texto or not texto.strip():
            raise ValidationError("El texto de búsqueda no puede estar vacío.")
        return self._repo.buscar(texto)
