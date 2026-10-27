from datetime import datetime, timedelta, timezone

import pytest

from app.domain.contenedor import Contenedor
from app.domain.lectura_sensor import LecturaSensor
from app.domain.sensor_iot import SensorIoT
from app.services.alerta_service import AlertaService
from app.services.sensor_inactivo_service import SensorInactivoService

pytestmark = pytest.mark.integration

_UMBRAL = 24.0


@pytest.fixture
def id_sensor_valido(contenedor_repo, sensor_iot_repo):
    id_contenedor = contenedor_repo.crear(
        Contenedor(codigo_internacional="TEST_SENSORINACT01", tipo="dry", capacidad=10.0)
    )
    return sensor_iot_repo.crear(SensorIoT(id_contenedor=id_contenedor, tipo="temperatura"))


def test_sensor_sin_lecturas_nunca_se_detecta_como_inactivo(id_sensor_valido, sensor_iot_repo):
    service = SensorInactivoService(sensor_repo=sensor_iot_repo)

    detectados = service.detectar(umbral_horas=_UMBRAL)

    assert any(s.id_sensor == id_sensor_valido for s in detectados)


def test_sensor_con_lectura_reciente_no_se_detecta(
    id_sensor_valido, sensor_iot_repo, lectura_sensor_repo, sensores_cassandra_usados
):
    sensores_cassandra_usados.append(id_sensor_valido)
    lectura_sensor_repo.crear(LecturaSensor(id_sensor=id_sensor_valido, temperatura=20.0))

    service = SensorInactivoService(sensor_repo=sensor_iot_repo, lectura_repo=lectura_sensor_repo)
    detectados = service.detectar(umbral_horas=_UMBRAL)

    assert not any(s.id_sensor == id_sensor_valido for s in detectados)


def test_sensor_con_lectura_vieja_se_detecta(
    id_sensor_valido, sensor_iot_repo, lectura_sensor_repo, sensores_cassandra_usados
):
    sensores_cassandra_usados.append(id_sensor_valido)
    lectura_sensor_repo.crear(
        LecturaSensor(
            id_sensor=id_sensor_valido,
            temperatura=20.0,
            fecha_hora=datetime.now(timezone.utc) - timedelta(hours=48),
        )
    )

    service = SensorInactivoService(sensor_repo=sensor_iot_repo, lectura_repo=lectura_sensor_repo)
    detectados = service.detectar(umbral_horas=_UMBRAL)

    assert any(s.id_sensor == id_sensor_valido for s in detectados)


def test_marcar_inactivos_actualiza_estado_y_genera_alerta(
    id_sensor_valido, sensor_iot_repo, lectura_sensor_repo, sensores_cassandra_usados, alertas_creadas
):
    service = SensorInactivoService(sensor_repo=sensor_iot_repo, lectura_repo=lectura_sensor_repo)

    marcados = service.marcar_inactivos(umbral_horas=_UMBRAL)

    assert any(s.id_sensor == id_sensor_valido for s in marcados)
    sensor = sensor_iot_repo.obtener_por_id(id_sensor_valido)
    assert sensor.estado == "inactivo"

    alertas = [a for a in AlertaService().listar_activas() if a.id_sensor == id_sensor_valido]
    assert len(alertas) == 1
    alertas_creadas.append(alertas[0].id_alerta)
    assert alertas[0].tipo == "sensor_inactivo"


def test_sensor_ya_inactivo_no_se_vuelve_a_detectar(id_sensor_valido, sensor_iot_repo):
    sensor = sensor_iot_repo.obtener_por_id(id_sensor_valido)
    sensor.estado = "inactivo"
    sensor_iot_repo.actualizar(sensor)

    service = SensorInactivoService(sensor_repo=sensor_iot_repo)
    detectados = service.detectar(umbral_horas=_UMBRAL)

    assert not any(s.id_sensor == id_sensor_valido for s in detectados)
