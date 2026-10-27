"""Tests de la lógica pura del simulador (sin DB): generación de valores
normales/anómalos y manejo de tipos de sensor desconocidos."""
from app.domain.sensor_iot import SensorIoT
from scripts.simulador_iot import _ANOMALIAS, _BASELINES, generar_lectura


def _sensor(tipo: str, id_sensor: int = 1) -> SensorIoT:
    return SensorIoT(id_contenedor=1, tipo=tipo, id_sensor=id_sensor)


def test_prob_anomalia_cero_nunca_marca_anomalia():
    sensor = _sensor("temperatura")
    for _ in range(20):
        _, es_anomalia = generar_lectura(sensor, prob_anomalia=0.0)
        assert es_anomalia is False


def test_prob_anomalia_uno_siempre_marca_anomalia_y_valor_en_rango():
    sensor = _sensor("temperatura")
    low, high = _ANOMALIAS["temperatura"]
    for _ in range(20):
        lectura, es_anomalia = generar_lectura(sensor, prob_anomalia=1.0)
        assert es_anomalia is True
        assert low <= lectura.temperatura <= high


def test_valor_normal_dentro_de_rango_razonable():
    sensor = _sensor("humedad")
    media, desvio = _BASELINES["humedad"]
    lectura, es_anomalia = generar_lectura(sensor, prob_anomalia=0.0)
    assert es_anomalia is False
    # dentro de +-5 desvíos estándar: prácticamente siempre cierto, no debería ser flaky
    assert media - 5 * desvio <= lectura.humedad <= media + 5 * desvio


def test_tipo_desconocido_no_marca_anomalia_ni_rompe():
    sensor = _sensor("gps")
    lectura, es_anomalia = generar_lectura(sensor, prob_anomalia=1.0)
    assert es_anomalia is False
    assert lectura.temperatura is None
    assert lectura.nivel_bateria is not None  # telemetría estándar igual se simula
    assert lectura.gps_lat is not None and lectura.gps_lon is not None


def test_sensor_tipo_bateria_no_duplica_nivel_bateria():
    sensor = _sensor("bateria")
    lectura, _ = generar_lectura(sensor, prob_anomalia=1.0)
    low, high = _ANOMALIAS["bateria"]
    assert low <= lectura.nivel_bateria <= high


def test_posicion_deriva_entre_llamadas():
    sensor = _sensor("temperatura", id_sensor=999)
    lectura1, _ = generar_lectura(sensor, prob_anomalia=0.0)
    lectura2, _ = generar_lectura(sensor, prob_anomalia=0.0)
    assert (lectura1.gps_lat, lectura1.gps_lon) != (lectura2.gps_lat, lectura2.gps_lon)
