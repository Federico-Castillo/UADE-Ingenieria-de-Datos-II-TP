import pytest

from app.domain.cliente import Cliente
from app.domain.envio import Envio
from app.domain.prediccion_riesgo import PrediccionRiesgo

pytestmark = pytest.mark.integration


@pytest.fixture
def id_envio_valido(cliente_repo, envio_repo):
    id_cliente = cliente_repo.crear(
        Cliente(razon_social="TEST_ClientePrediccion", cuit="90-70000003-1", email="prediccion1@example.com")
    )
    return envio_repo.crear(Envio(id_cliente=id_cliente, origen="TEST_Salta", destino="Jujuy"))


def test_crear_y_obtener_ultima(prediccion_riesgo_repo, id_envio_valido, predicciones_creadas):
    id_prediccion = prediccion_riesgo_repo.crear(
        PrediccionRiesgo(id_envio=id_envio_valido, probabilidad_demora=0.3, riesgo_climatico=0.2)
    )
    predicciones_creadas.append(id_prediccion)

    ultima = prediccion_riesgo_repo.ultima_por_envio(id_envio_valido)

    assert ultima is not None
    assert ultima.probabilidad_demora == 0.3


def test_ultima_devuelve_la_mas_reciente(prediccion_riesgo_repo, id_envio_valido, predicciones_creadas):
    id_1 = prediccion_riesgo_repo.crear(PrediccionRiesgo(id_envio=id_envio_valido, probabilidad_demora=0.1))
    predicciones_creadas.append(id_1)
    id_2 = prediccion_riesgo_repo.crear(PrediccionRiesgo(id_envio=id_envio_valido, probabilidad_demora=0.9))
    predicciones_creadas.append(id_2)

    ultima = prediccion_riesgo_repo.ultima_por_envio(id_envio_valido)

    assert ultima.id_prediccion == id_2
    assert ultima.probabilidad_demora == 0.9


def test_listar_por_envio(prediccion_riesgo_repo, id_envio_valido, predicciones_creadas):
    id_prediccion = prediccion_riesgo_repo.crear(
        PrediccionRiesgo(id_envio=id_envio_valido, probabilidad_demora=0.5)
    )
    predicciones_creadas.append(id_prediccion)

    predicciones = prediccion_riesgo_repo.listar_por_envio(id_envio_valido)

    assert any(p.id_prediccion == id_prediccion for p in predicciones)
