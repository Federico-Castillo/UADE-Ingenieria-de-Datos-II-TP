from app.core.exceptions import NotFoundError, ValidationError
from app.domain.factura import Factura
from app.repositories.cliente_repository import ClienteRepository
from app.repositories.factura_repository import FacturaRepository


class FacturaService:
    def __init__(
        self,
        repository: FacturaRepository | None = None,
        cliente_repository: ClienteRepository | None = None,
    ):
        self._repo = repository or FacturaRepository()
        self._cliente_repo = cliente_repository or ClienteRepository()

    def dar_alta(self, factura: Factura) -> Factura:
        if factura.importe_total <= 0:
            raise ValidationError("El importe total debe ser mayor a cero.")
        if self._cliente_repo.obtener_por_id(factura.id_cliente) is None:
            raise ValidationError(f"No existe el cliente con id {factura.id_cliente}.")
        id_factura = self._repo.crear(factura)
        factura.id_factura = id_factura
        return factura

    def obtener_por_id(self, id_factura: int) -> Factura:
        factura = self._repo.obtener_por_id(id_factura)
        if factura is None:
            raise NotFoundError(f"No existe una factura con id {id_factura}.")
        return factura

    def listar(self) -> list[Factura]:
        return self._repo.listar()

    def listar_por_cliente(self, id_cliente: int) -> list[Factura]:
        if self._cliente_repo.obtener_por_id(id_cliente) is None:
            raise ValidationError(f"No existe el cliente con id {id_cliente}.")
        return self._repo.listar_por_cliente(id_cliente)
