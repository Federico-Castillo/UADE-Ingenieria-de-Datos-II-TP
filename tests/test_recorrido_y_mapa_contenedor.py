import os
from datetime import datetime, timedelta, timezone

import pytest

from app.core.exceptions import ValidationError
from app.domain.contenedor import Contenedor
from app.domain.lectura_sensor import LecturaSensor
from app.domain.sensor_iot import SensorIoT
from app.services.lectura_sensor_service import LecturaSensorService
from app.services.mapa_service import MapaService

pytestmark = pytest.mark.integration


@pytest.fixture
def contenedor_con_dos_sensores(contenedor_repo, sensor_iot_repo):
    id_contenedor = contenedor_repo.crear(
        Contenedor(codigo_internacional="TEST_MAPA01", tipo="dry", capacidad=10.0)
    )
    id_sensor_1 = sensor_iot_repo.crear(SensorIoT(id_contenedor=id_contenedor, tipo="temperatura"))
    id_sensor_2 = sensor_iot_repo.crear(SensorIoT(id_contenedor=id_contenedor, tipo="humedad"))
    return id_contenedor, id_sensor_1, id_sensor_2


def test_listar_por_contenedor_combina_y_ordena_lecturas_de_varios_sensores(
    contenedor_con_dos_sensores, lectura_sensor_repo, sensores_cassandra_usados
):
    id_contenedor, id_sensor_1, id_sensor_2 = contenedor_con_dos_sensores
    sensores_cassandra_usados.append(id_sensor_1)
    sensores_cassandra_usados.append(id_sensor_2)
    ahora = datetime.now(timezone.utc)

    mas_vieja = lectura_sensor_repo.crear(
        LecturaSensor(id_sensor=id_sensor_1, gps_lat=-34.6, gps_lon=-58.4, fecha_hora=ahora - timedelta(hours=2))
    )
    intermedia = lectura_sensor_repo.crear(
        LecturaSensor(id_sensor=id_sensor_2, gps_lat=-33.0, gps_lon=-59.0, fecha_hora=ahora - timedelta(hours=1))
    )
    mas_nueva = lectura_sensor_repo.crear(
        LecturaSensor(id_sensor=id_sensor_1, gps_lat=-32.0, gps_lon=-60.0, fecha_hora=ahora)
    )

    lecturas = LecturaSensorService().listar_por_contenedor(id_contenedor)

    ids_en_orden = [l.id_lectura for l in lecturas]
    assert ids_en_orden == [mas_vieja.id_lectura, intermedia.id_lectura, mas_nueva.id_lectura]


def test_listar_por_contenedor_rechaza_contenedor_inexistente():
    with pytest.raises(ValidationError):
        LecturaSensorService().listar_por_contenedor(999999999)


def test_generar_mapa_contenedor_crea_un_archivo_html(
    contenedor_con_dos_sensores, lectura_sensor_repo, sensores_cassandra_usados
):
    id_contenedor, id_sensor_1, _ = contenedor_con_dos_sensores
    sensores_cassandra_usados.append(id_sensor_1)
    lectura_sensor_repo.crear(LecturaSensor(id_sensor=id_sensor_1, gps_lat=-34.6, gps_lon=-58.4))
    lectura_sensor_repo.crear(LecturaSensor(id_sensor=id_sensor_1, gps_lat=-33.0, gps_lon=-59.0))

    ruta = MapaService().generar_mapa_contenedor(id_contenedor)

    try:
        assert os.path.isfile(ruta)
        with open(ruta, encoding="utf-8") as f:
            contenido = f.read()
        assert "leaflet" in contenido.lower()
    finally:
        os.remove(ruta)


def test_generar_mapa_sin_lecturas_gps_lanza_validation_error(contenedor_con_dos_sensores):
    id_contenedor, _, _ = contenedor_con_dos_sensores

    with pytest.raises(ValidationError):
        MapaService().generar_mapa_contenedor(id_contenedor)
