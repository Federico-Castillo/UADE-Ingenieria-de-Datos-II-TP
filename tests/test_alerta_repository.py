import pytest

pytestmark = pytest.mark.integration

_ID_SENSOR_TEST = 900001
_ID_REGLA_TEST = 900002


def test_crear_y_obtener(alerta_repo, alertas_creadas):
    alerta = alerta_repo.crear(_ID_SENSOR_TEST, _ID_REGLA_TEST, "temperatura_alta")
    alertas_creadas.append(alerta.id_alerta)

    recuperada = alerta_repo.obtener(alerta.id_alerta)

    assert recuperada is not None
    assert recuperada.id_sensor == _ID_SENSOR_TEST
    assert recuperada.id_regla == _ID_REGLA_TEST
    assert recuperada.estado == "activa"


def test_listar_activas_incluye_la_creada(alerta_repo, alertas_creadas):
    alerta = alerta_repo.crear(_ID_SENSOR_TEST, _ID_REGLA_TEST, "humedad_alta")
    alertas_creadas.append(alerta.id_alerta)

    activas = alerta_repo.listar_activas()

    assert any(a.id_alerta == alerta.id_alerta for a in activas)


def test_resolver_elimina_la_alerta(alerta_repo):
    alerta = alerta_repo.crear(_ID_SENSOR_TEST, _ID_REGLA_TEST, "bateria_baja")

    resuelta = alerta_repo.resolver(alerta.id_alerta)

    assert resuelta is True
    assert alerta_repo.obtener(alerta.id_alerta) is None
    assert alerta.id_alerta not in [a.id_alerta for a in alerta_repo.listar_activas()]


def test_resolver_alerta_inexistente_devuelve_false(alerta_repo):
    assert alerta_repo.resolver("id-que-no-existe") is False
