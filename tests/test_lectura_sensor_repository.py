from datetime import datetime, timedelta, timezone

import pytest

from app.domain.lectura_sensor import LecturaSensor

pytestmark = pytest.mark.integration

_ID_SENSOR_TEST = 900101


def test_crear_y_listar_por_sensor(lectura_sensor_repo, sensores_cassandra_usados):
    sensores_cassandra_usados.append(_ID_SENSOR_TEST)

    creada = lectura_sensor_repo.crear(LecturaSensor(id_sensor=_ID_SENSOR_TEST, temperatura=21.5))

    assert creada.id_lectura is not None
    lecturas = lectura_sensor_repo.listar_por_sensor(_ID_SENSOR_TEST)
    assert any(l.id_lectura == creada.id_lectura for l in lecturas)


def test_ultima_por_sensor_devuelve_la_mas_reciente(lectura_sensor_repo, sensores_cassandra_usados):
    sensores_cassandra_usados.append(_ID_SENSOR_TEST + 1)
    id_sensor = _ID_SENSOR_TEST + 1

    primera = lectura_sensor_repo.crear(
        LecturaSensor(id_sensor=id_sensor, temperatura=20.0, fecha_hora=datetime.now(timezone.utc) - timedelta(minutes=5))
    )
    segunda = lectura_sensor_repo.crear(LecturaSensor(id_sensor=id_sensor, temperatura=25.0))

    ultima = lectura_sensor_repo.ultima_por_sensor(id_sensor)

    assert ultima.id_lectura == segunda.id_lectura
    assert ultima.id_lectura != primera.id_lectura


def test_listar_por_rango(lectura_sensor_repo, sensores_cassandra_usados):
    sensores_cassandra_usados.append(_ID_SENSOR_TEST + 2)
    id_sensor = _ID_SENSOR_TEST + 2
    ahora = datetime.now(timezone.utc)

    dentro_del_rango = lectura_sensor_repo.crear(
        LecturaSensor(id_sensor=id_sensor, temperatura=24.0, fecha_hora=ahora)
    )
    lectura_sensor_repo.crear(
        LecturaSensor(id_sensor=id_sensor, temperatura=24.0, fecha_hora=ahora - timedelta(days=2))
    )

    resultado = lectura_sensor_repo.listar_por_rango(
        id_sensor, ahora - timedelta(hours=1), ahora + timedelta(hours=1)
    )

    ids = [l.id_lectura for l in resultado]
    assert dentro_del_rango.id_lectura in ids
    assert len(resultado) == 1
