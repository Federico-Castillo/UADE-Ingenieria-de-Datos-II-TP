from app.core.exceptions import NotFoundError, ValidationError
from app.domain.alerta import Alerta
from app.repositories.alerta_repository import AlertaRepository
from app.repositories.regla_repository import ReglaRepository
from app.repositories.sensor_iot_repository import SensorIoTRepository


class AlertaService:
    def __init__(
        self,
        repository: AlertaRepository | None = None,
        regla_repository: ReglaRepository | None = None,
        sensor_repository: SensorIoTRepository | None = None,
    ):
        self._repo = repository or AlertaRepository()
        self._regla_repo = regla_repository or ReglaRepository()
        self._sensor_repo = sensor_repository or SensorIoTRepository()

    def generar_alerta(self, id_sensor: int, id_regla: int, id_evento: str | None = None) -> Alerta:
        if self._sensor_repo.obtener_por_id(id_sensor) is None:
            raise ValidationError(f"No existe el sensor con id {id_sensor}.")
        regla = self._regla_repo.obtener_por_id(id_regla)
        if regla is None:
            raise ValidationError(f"No existe la regla con id {id_regla}.")
        tipo = f"{regla.tipo_sensor}_{regla.severidad}"
        return self._repo.crear(id_sensor, id_regla, tipo, id_evento)

    def resolver(self, id_alerta: str) -> None:
        resuelta = self._repo.resolver(id_alerta)
        if not resuelta:
            raise NotFoundError(f"No existe una alerta activa con id {id_alerta}.")

    def obtener(self, id_alerta: str) -> Alerta:
        alerta = self._repo.obtener(id_alerta)
        if alerta is None:
            raise NotFoundError(f"No existe una alerta activa con id {id_alerta}.")
        return alerta

    def listar_activas(self) -> list[Alerta]:
        return self._repo.listar_activas()
