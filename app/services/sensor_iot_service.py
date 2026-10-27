from app.core.exceptions import NotFoundError, ValidationError
from app.domain.sensor_iot import SensorIoT
from app.repositories.contenedor_repository import ContenedorRepository
from app.repositories.sensor_iot_repository import SensorIoTRepository


class SensorIoTService:
    def __init__(
        self,
        repository: SensorIoTRepository | None = None,
        contenedor_repository: ContenedorRepository | None = None,
    ):
        self._repo = repository or SensorIoTRepository()
        self._contenedor_repo = contenedor_repository or ContenedorRepository()

    def _validar(self, sensor: SensorIoT) -> None:
        if not sensor.tipo or not sensor.tipo.strip():
            raise ValidationError("El tipo de sensor no puede estar vacío.")
        if self._contenedor_repo.obtener_por_id(sensor.id_contenedor) is None:
            raise ValidationError(f"No existe el contenedor con id {sensor.id_contenedor}.")

    def dar_alta(self, sensor: SensorIoT) -> SensorIoT:
        self._validar(sensor)
        id_sensor = self._repo.crear(sensor)
        sensor.id_sensor = id_sensor
        return sensor

    def modificar(self, sensor: SensorIoT) -> None:
        if sensor.id_sensor is None:
            raise ValidationError("No se puede modificar un sensor sin id_sensor.")
        self._validar(sensor)
        if self._repo.obtener_por_id(sensor.id_sensor) is None:
            raise NotFoundError(f"No existe un sensor con id {sensor.id_sensor}.")
        self._repo.actualizar(sensor)

    def eliminar(self, id_sensor: int) -> None:
        if self._repo.obtener_por_id(id_sensor) is None:
            raise NotFoundError(f"No existe un sensor con id {id_sensor}.")
        self._repo.eliminar(id_sensor)

    def obtener_por_id(self, id_sensor: int) -> SensorIoT:
        sensor = self._repo.obtener_por_id(id_sensor)
        if sensor is None:
            raise NotFoundError(f"No existe un sensor con id {id_sensor}.")
        return sensor

    def listar(self) -> list[SensorIoT]:
        return self._repo.listar()

    def listar_por_contenedor(self, id_contenedor: int) -> list[SensorIoT]:
        if self._contenedor_repo.obtener_por_id(id_contenedor) is None:
            raise ValidationError(f"No existe el contenedor con id {id_contenedor}.")
        return self._repo.listar_por_contenedor(id_contenedor)
