from app.core.exceptions import NotFoundError, ValidationError
from app.domain.vehiculo import Vehiculo
from app.repositories.vehiculo_repository import VehiculoRepository


class VehiculoService:
    def __init__(self, repository: VehiculoRepository | None = None):
        self._repo = repository or VehiculoRepository()

    def _validar(self, vehiculo: Vehiculo) -> None:
        if not vehiculo.tipo or not vehiculo.tipo.strip():
            raise ValidationError("El tipo no puede estar vacío.")
        if not vehiculo.identificacion or not vehiculo.identificacion.strip():
            raise ValidationError("La identificación no puede estar vacía.")
        if not vehiculo.empresa_operadora or not vehiculo.empresa_operadora.strip():
            raise ValidationError("La empresa operadora no puede estar vacía.")

    def dar_alta(self, vehiculo: Vehiculo) -> Vehiculo:
        self._validar(vehiculo)
        id_vehiculo = self._repo.crear(vehiculo)
        vehiculo.id_vehiculo = id_vehiculo
        return vehiculo

    def modificar(self, vehiculo: Vehiculo) -> None:
        if vehiculo.id_vehiculo is None:
            raise ValidationError("No se puede modificar un vehículo sin id_vehiculo.")
        self._validar(vehiculo)
        if self._repo.obtener_por_id(vehiculo.id_vehiculo) is None:
            raise NotFoundError(f"No existe un vehículo con id {vehiculo.id_vehiculo}.")
        self._repo.actualizar(vehiculo)

    def eliminar(self, id_vehiculo: int) -> None:
        if self._repo.obtener_por_id(id_vehiculo) is None:
            raise NotFoundError(f"No existe un vehículo con id {id_vehiculo}.")
        self._repo.eliminar(id_vehiculo)

    def obtener_por_id(self, id_vehiculo: int) -> Vehiculo:
        vehiculo = self._repo.obtener_por_id(id_vehiculo)
        if vehiculo is None:
            raise NotFoundError(f"No existe un vehículo con id {id_vehiculo}.")
        return vehiculo

    def listar(self) -> list[Vehiculo]:
        return self._repo.listar()
