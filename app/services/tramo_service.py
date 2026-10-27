from app.core.exceptions import ValidationError
from app.domain.tramo import Tramo
from app.repositories.cliente_repository import ClienteRepository
from app.repositories.envio_repository import EnvioRepository
from app.repositories.operador_logistico_repository import OperadorLogisticoRepository
from app.repositories.tramo_repository import TramoRepository
from app.repositories.vehiculo_repository import VehiculoRepository

_MEDIOS_VALIDOS = {"terrestre", "maritimo", "aereo"}


class TramoService:
    def __init__(
        self,
        repository: TramoRepository | None = None,
        envio_repository: EnvioRepository | None = None,
        cliente_repository: ClienteRepository | None = None,
        vehiculo_repository: VehiculoRepository | None = None,
        operador_repository: OperadorLogisticoRepository | None = None,
    ):
        self._repo = repository or TramoRepository()
        self._envio_repo = envio_repository or EnvioRepository()
        self._cliente_repo = cliente_repository or ClienteRepository()
        self._vehiculo_repo = vehiculo_repository or VehiculoRepository()
        self._operador_repo = operador_repository or OperadorLogisticoRepository()

    def registrar_tramo(self, tramo: Tramo) -> Tramo:
        if tramo.medio_transporte not in _MEDIOS_VALIDOS:
            raise ValidationError(f"Medio de transporte inválido. Opciones: {', '.join(sorted(_MEDIOS_VALIDOS))}.")
        if not tramo.origen_nombre or not tramo.destino_nombre:
            raise ValidationError("Origen y destino no pueden estar vacíos.")

        envio = self._envio_repo.obtener_por_id(tramo.id_envio)
        if envio is None:
            raise ValidationError(f"No existe el envío con id {tramo.id_envio}.")
        cliente = self._cliente_repo.obtener_por_id(envio.id_cliente)
        if cliente is None:
            raise ValidationError(f"No existe el cliente con id {envio.id_cliente}.")
        vehiculo = self._vehiculo_repo.obtener_por_id(tramo.id_vehiculo)
        if vehiculo is None:
            raise ValidationError(f"No existe el vehículo con id {tramo.id_vehiculo}.")
        operador = self._operador_repo.obtener_por_id(tramo.id_operador_logistico)
        if operador is None:
            raise ValidationError(f"No existe el operador logístico con id {tramo.id_operador_logistico}.")

        return self._repo.crear(
            tramo,
            cliente_razon_social=cliente.razon_social,
            envio_estado=envio.estado,
            envio_prioridad=envio.prioridad,
            vehiculo_tipo=vehiculo.tipo,
            vehiculo_identificacion=vehiculo.identificacion,
            operador_nombre=operador.razon_social,
            id_cliente=cliente.id_cliente,
        )

    def ruta_completa(self, id_envio: int) -> list[dict]:
        if self._envio_repo.obtener_por_id(id_envio) is None:
            raise ValidationError(f"No existe el envío con id {id_envio}.")
        return self._repo.ruta_completa(id_envio)

    def red_relaciones(self) -> list[dict]:
        return self._repo.red_relaciones()
