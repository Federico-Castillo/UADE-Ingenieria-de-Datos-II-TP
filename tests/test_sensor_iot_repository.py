import pytest

from app.domain.contenedor import Contenedor
from app.domain.sensor_iot import SensorIoT

pytestmark = pytest.mark.integration


@pytest.fixture
def id_contenedor_valido(contenedor_repo):
    return contenedor_repo.crear(
        Contenedor(codigo_internacional="TEST_CONTSENSOR", tipo="dry", capacidad=10.0)
    )


def _sensor(id_contenedor: int, **kwargs) -> SensorIoT:
    defaults = dict(tipo="temperatura")
    defaults.update(kwargs)
    return SensorIoT(id_contenedor=id_contenedor, **defaults)


def test_crear_y_recuperar_por_id(sensor_iot_repo, id_contenedor_valido):
    id_sensor = sensor_iot_repo.crear(_sensor(id_contenedor_valido))

    recuperado = sensor_iot_repo.obtener_por_id(id_sensor)

    assert recuperado is not None
    assert recuperado.id_contenedor == id_contenedor_valido
    assert recuperado.tipo == "temperatura"


def test_listar_por_contenedor(sensor_iot_repo, id_contenedor_valido):
    id_sensor = sensor_iot_repo.crear(_sensor(id_contenedor_valido, tipo="humedad"))

    sensores = sensor_iot_repo.listar_por_contenedor(id_contenedor_valido)

    assert any(s.id_sensor == id_sensor for s in sensores)


def test_actualizar_modifica_los_campos(sensor_iot_repo, id_contenedor_valido):
    id_sensor = sensor_iot_repo.crear(_sensor(id_contenedor_valido))
    sensor = sensor_iot_repo.obtener_por_id(id_sensor)

    sensor.estado = "inactivo"
    sensor_iot_repo.actualizar(sensor)

    recuperado = sensor_iot_repo.obtener_por_id(id_sensor)
    assert recuperado.estado == "inactivo"


def test_eliminar_borra_la_fila(sensor_iot_repo, id_contenedor_valido):
    id_sensor = sensor_iot_repo.crear(_sensor(id_contenedor_valido))

    sensor_iot_repo.eliminar(id_sensor)

    assert sensor_iot_repo.obtener_por_id(id_sensor) is None
