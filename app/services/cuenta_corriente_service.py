from app.core.exceptions import ValidationError
from app.domain.cuenta_corriente import CuentaCorriente
from app.repositories.cliente_repository import ClienteRepository
from app.repositories.cuenta_corriente_repository import CuentaCorrienteRepository


class CuentaCorrienteService:
    def __init__(
        self,
        repository: CuentaCorrienteRepository | None = None,
        cliente_repository: ClienteRepository | None = None,
    ):
        self._repo = repository or CuentaCorrienteRepository()
        self._cliente_repo = cliente_repository or ClienteRepository()

    def obtener_por_cliente(self, id_cliente: int) -> CuentaCorriente:
        if self._cliente_repo.obtener_por_id(id_cliente) is None:
            raise ValidationError(f"No existe el cliente con id {id_cliente}.")
        cuenta = self._repo.obtener_por_cliente(id_cliente)
        # Un cliente sin facturas todavía "tiene" cuenta corriente con saldo 0,
        # aunque no exista fila física (se crea recién con la primera factura).
        return cuenta if cuenta is not None else CuentaCorriente(id_cliente=id_cliente, saldo=0.0)

    def listar(self) -> list[CuentaCorriente]:
        return self._repo.listar()
