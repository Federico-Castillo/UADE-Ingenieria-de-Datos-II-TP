from app.core.exceptions import NotFoundError, ValidationError
from app.domain.factura_recibida import FacturaRecibida
from app.repositories.factura_recibida_repository import FacturaRecibidaRepository
from app.repositories.operador_logistico_repository import OperadorLogisticoRepository
from app.repositories.proveedor_repository import ProveedorRepository


class FacturaRecibidaService:
    def __init__(
        self,
        repository: FacturaRecibidaRepository | None = None,
        proveedor_repository: ProveedorRepository | None = None,
        operador_repository: OperadorLogisticoRepository | None = None,
    ):
        self._repo = repository or FacturaRecibidaRepository()
        self._proveedor_repo = proveedor_repository or ProveedorRepository()
        self._operador_repo = operador_repository or OperadorLogisticoRepository()

    def _validar(self, factura: FacturaRecibida) -> None:
        if factura.importe_total <= 0:
            raise ValidationError("El importe total debe ser mayor a cero.")
        tiene_proveedor = factura.id_proveedor is not None
        tiene_operador = factura.id_operador_logistico is not None
        if tiene_proveedor == tiene_operador:
            raise ValidationError(
                "La factura debe pertenecer a exactamente un proveedor o un operador logístico, no ambos ni ninguno."
            )
        if tiene_proveedor and self._proveedor_repo.obtener_por_id(factura.id_proveedor) is None:
            raise ValidationError(f"No existe el proveedor con id {factura.id_proveedor}.")
        if tiene_operador and self._operador_repo.obtener_por_id(factura.id_operador_logistico) is None:
            raise ValidationError(f"No existe el operador logístico con id {factura.id_operador_logistico}.")

    def dar_alta(self, factura: FacturaRecibida) -> FacturaRecibida:
        self._validar(factura)
        id_factura = self._repo.crear(factura)
        factura.id_factura_recibida = id_factura
        return factura

    def obtener_por_id(self, id_factura_recibida: int) -> FacturaRecibida:
        factura = self._repo.obtener_por_id(id_factura_recibida)
        if factura is None:
            raise NotFoundError(f"No existe una factura recibida con id {id_factura_recibida}.")
        return factura

    def listar(self) -> list[FacturaRecibida]:
        return self._repo.listar()

    def listar_por_proveedor(self, id_proveedor: int) -> list[FacturaRecibida]:
        if self._proveedor_repo.obtener_por_id(id_proveedor) is None:
            raise ValidationError(f"No existe el proveedor con id {id_proveedor}.")
        return self._repo.listar_por_proveedor(id_proveedor)

    def listar_por_operador(self, id_operador_logistico: int) -> list[FacturaRecibida]:
        if self._operador_repo.obtener_por_id(id_operador_logistico) is None:
            raise ValidationError(f"No existe el operador logístico con id {id_operador_logistico}.")
        return self._repo.listar_por_operador(id_operador_logistico)
