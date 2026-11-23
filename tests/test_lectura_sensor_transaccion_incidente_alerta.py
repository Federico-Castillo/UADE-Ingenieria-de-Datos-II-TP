"""Transacción cross-engine Incidente(Mongo)+Alerta(Redis) con rollback
manual (ver LecturaSensorService._registrar_incidente_y_alerta_transaccional).
Se prueba con repositorios/servicios falsos -- lo que importa acá es la
coordinación entre los dos motores, no probar Mongo/Redis reales (eso ya lo
cubre test_lectura_sensor_pipeline.py, de integración)."""
from app.core.exceptions import RepositoryError, TransaccionCrossEngineError
from app.domain.lectura_sensor import LecturaSensor
from app.domain.regla import Regla
from app.domain.sensor_iot import SensorIoT
from app.services.lectura_sensor_service import LecturaSensorService


class _FakeLecturaRepo:
    def crear(self, lectura):
        lectura.id_lectura = "fake-lectura-1"
        return lectura


class _FakeSensorRepo:
    def __init__(self, sensor):
        self._sensor = sensor

    def obtener_por_id(self, id_sensor):
        return self._sensor


class _FakeReglaRepo:
    def __init__(self, reglas):
        self._reglas = reglas

    def listar_por_tipo_sensor(self, tipo_sensor):
        return self._reglas


class _FakeEnvioContenedorRepo:
    def __init__(self, id_envio):
        self._id_envio = id_envio

    def envio_actual_de_contenedor(self, id_contenedor):
        return self._id_envio


class _FakeIncidenteService:
    def __init__(self):
        self.creados = []
        self.eliminados = []

    def registrar(self, incidente):
        incidente.id_incidente = f"incidente-{len(self.creados)}"
        self.creados.append(incidente.id_incidente)
        return incidente

    def eliminar(self, id_incidente):
        self.eliminados.append(id_incidente)
        self.creados.remove(id_incidente)


class _FakeAlertaServiceFalla:
    def __init__(self):
        self.llamadas = []

    def generar_alerta(self, id_sensor, id_regla, id_evento=None):
        self.llamadas.append(id_evento)
        raise RepositoryError("Redis caído (simulado)")


class _FakeAlertaServiceOk:
    def __init__(self):
        self.llamadas = []

    def generar_alerta(self, id_sensor, id_regla, id_evento=None):
        self.llamadas.append(id_evento)


def _service(incidente_service, alerta_service, id_envio=1):
    sensor = SensorIoT(id_contenedor=10, tipo="temperatura", id_sensor=1)
    regla = Regla(
        nombre="TEST_Regla", tipo_sensor="temperatura", operador_comparacion=">",
        valor_umbral=30.0, severidad="critica", id_usuario_creador=1, id_regla=1,
    )
    return LecturaSensorService(
        repository=_FakeLecturaRepo(),
        sensor_repository=_FakeSensorRepo(sensor),
        regla_repository=_FakeReglaRepo([regla]),
        envio_contenedor_repository=_FakeEnvioContenedorRepo(id_envio),
        incidente_service=incidente_service,
        alerta_service=alerta_service,
    )


def test_alerta_fallida_revierte_el_incidente():
    incidente_service = _FakeIncidenteService()
    alerta_service = _FakeAlertaServiceFalla()
    service = _service(incidente_service, alerta_service)

    # El pipeline nunca debe hacer fallar el registro de la lectura, aunque
    # la transacción incidente+alerta falle y se revierta.
    service.registrar_lectura(LecturaSensor(id_sensor=1, temperatura=38.0))

    assert incidente_service.creados == []
    assert incidente_service.eliminados == ["incidente-0"]
    assert alerta_service.llamadas == ["incidente-0"]


def test_alerta_exitosa_no_revierte_el_incidente():
    incidente_service = _FakeIncidenteService()
    alerta_service = _FakeAlertaServiceOk()
    service = _service(incidente_service, alerta_service)

    service.registrar_lectura(LecturaSensor(id_sensor=1, temperatura=38.0))

    assert incidente_service.creados == ["incidente-0"]
    assert incidente_service.eliminados == []
    assert alerta_service.llamadas == ["incidente-0"]


def test_transaccion_fallida_propaga_tipo_de_error_correcto_internamente():
    incidente_service = _FakeIncidenteService()
    alerta_service = _FakeAlertaServiceFalla()
    service = _service(incidente_service, alerta_service)

    try:
        service._registrar_incidente_y_alerta_transaccional(
            sensor=SensorIoT(id_contenedor=10, tipo="temperatura", id_sensor=1),
            regla=Regla(
                nombre="TEST_Regla", tipo_sensor="temperatura", operador_comparacion=">",
                valor_umbral=30.0, severidad="critica", id_usuario_creador=1, id_regla=1,
            ),
            id_envio=1,
        )
        assert False, "debería haber propagado TransaccionCrossEngineError"
    except TransaccionCrossEngineError:
        pass

    assert incidente_service.creados == []
    assert incidente_service.eliminados == ["incidente-0"]
