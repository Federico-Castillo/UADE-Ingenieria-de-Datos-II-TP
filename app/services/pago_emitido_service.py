from app.core.exceptions import NotFoundError, ValidationError
from app.domain.pago_emitido import PagoEmitido
from app.repositories.factura_recibida_repository import FacturaRecibidaRepository
from app.repositories.pago_emitido_repository import PagoEmitidoRepository


class PagoEmitidoService:
    def __init__(
        self,
        repository: PagoEmitidoRepository | None = None,
        factura_repository: FacturaRecibidaRepository | None = None,
    ):
        self._repo = repository or PagoEmitidoRepository()
        self._factura_repo = factura_repository or FacturaRecibidaRepository()

    def registrar_pago(self, pago: PagoEmitido) -> PagoEmitido:
        if pago.monto <= 0:
            raise ValidationError("El monto debe ser mayor a cero.")
        if not pago.medio_pago or not pago.medio_pago.strip():
            raise ValidationError("El medio de pago no puede estar vacío.")
        if self._factura_repo.obtener_por_id(pago.id_factura_recibida) is None:
            raise ValidationError(f"No existe la factura recibida con id {pago.id_factura_recibida}.")
        id_pago = self._repo.crear(pago)
        pago.id_pago_emitido = id_pago
        return pago

    def obtener_por_id(self, id_pago_emitido: int) -> PagoEmitido:
        pago = self._repo.obtener_por_id(id_pago_emitido)
        if pago is None:
            raise NotFoundError(f"No existe un pago con id {id_pago_emitido}.")
        return pago

    def listar_por_factura(self, id_factura_recibida: int) -> list[PagoEmitido]:
        if self._factura_repo.obtener_por_id(id_factura_recibida) is None:
            raise ValidationError(f"No existe la factura recibida con id {id_factura_recibida}.")
        return self._repo.listar_por_factura(id_factura_recibida)
