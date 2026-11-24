from app.core.exceptions import NotFoundError, ValidationError
from app.domain.pago import MEDIOS_PAGO_VALIDOS, Pago
from app.repositories.factura_repository import FacturaRepository
from app.repositories.pago_repository import PagoRepository


class PagoService:
    def __init__(
        self,
        repository: PagoRepository | None = None,
        factura_repository: FacturaRepository | None = None,
    ):
        self._repo = repository or PagoRepository()
        self._factura_repo = factura_repository or FacturaRepository()

    def registrar_pago(self, pago: Pago) -> Pago:
        if pago.monto <= 0:
            raise ValidationError("El monto debe ser mayor a cero.")
        if pago.medio_pago not in MEDIOS_PAGO_VALIDOS:
            raise ValidationError(f"El medio de pago debe ser uno de: {', '.join(MEDIOS_PAGO_VALIDOS)}.")
        if self._factura_repo.obtener_por_id(pago.id_factura) is None:
            raise ValidationError(f"No existe la factura con id {pago.id_factura}.")
        id_pago = self._repo.crear(pago)
        pago.id_pago = id_pago
        return pago

    def obtener_por_id(self, id_pago: int) -> Pago:
        pago = self._repo.obtener_por_id(id_pago)
        if pago is None:
            raise NotFoundError(f"No existe un pago con id {id_pago}.")
        return pago

    def listar_por_factura(self, id_factura: int) -> list[Pago]:
        if self._factura_repo.obtener_por_id(id_factura) is None:
            raise ValidationError(f"No existe la factura con id {id_factura}.")
        return self._repo.listar_por_factura(id_factura)
