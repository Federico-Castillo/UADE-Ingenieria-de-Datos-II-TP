from app.core.exceptions import ValidationError
from app.domain.cuenta_corriente_pagable import CuentaCorrientePagable
from app.repositories.cuenta_corriente_pagable_repository import CuentaCorrientePagableRepository
from app.repositories.operador_logistico_repository import OperadorLogisticoRepository
from app.repositories.proveedor_repository import ProveedorRepository


class CuentaCorrientePagableService:
    def __init__(
        self,
        repository: CuentaCorrientePagableRepository | None = None,
        proveedor_repository: ProveedorRepository | None = None,
        operador_repository: OperadorLogisticoRepository | None = None,
    ):
        self._repo = repository or CuentaCorrientePagableRepository()
        self._proveedor_repo = proveedor_repository or ProveedorRepository()
        self._operador_repo = operador_repository or OperadorLogisticoRepository()

    def obtener_por_proveedor(self, id_proveedor: int) -> CuentaCorrientePagable:
        if self._proveedor_repo.obtener_por_id(id_proveedor) is None:
            raise ValidationError(f"No existe el proveedor con id {id_proveedor}.")
        cuenta = self._repo.obtener_por_proveedor(id_proveedor)
        return cuenta if cuenta is not None else CuentaCorrientePagable(id_proveedor=id_proveedor, saldo=0.0)

    def obtener_por_operador(self, id_operador_logistico: int) -> CuentaCorrientePagable:
        if self._operador_repo.obtener_por_id(id_operador_logistico) is None:
            raise ValidationError(f"No existe el operador logístico con id {id_operador_logistico}.")
        cuenta = self._repo.obtener_por_operador(id_operador_logistico)
        return (
            cuenta
            if cuenta is not None
            else CuentaCorrientePagable(id_operador_logistico=id_operador_logistico, saldo=0.0)
        )

    def listar(self) -> list[CuentaCorrientePagable]:
        return self._repo.listar()
