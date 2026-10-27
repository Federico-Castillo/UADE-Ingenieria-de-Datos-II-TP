import pytest

from app.domain.cliente import Cliente
from app.domain.envio import Envio

pytestmark = pytest.mark.integration


@pytest.fixture
def id_cliente_valido(cliente_repo):
    return cliente_repo.crear(
        Cliente(razon_social="TEST_ClienteEnvio", cuit="90-40000001-1", email="envio1@example.com")
    )


def _envio(id_cliente: int, origen: str = "TEST_Buenos Aires", **kwargs) -> Envio:
    defaults = dict(destino="Mendoza")
    defaults.update(kwargs)
    return Envio(id_cliente=id_cliente, origen=origen, **defaults)


def test_crear_y_recuperar_por_id(envio_repo, id_cliente_valido):
    id_envio = envio_repo.crear(_envio(id_cliente_valido))

    recuperado = envio_repo.obtener_por_id(id_envio)

    assert recuperado is not None
    assert recuperado.id_cliente == id_cliente_valido
    assert recuperado.origen == "TEST_Buenos Aires"


def test_listar_por_cliente(envio_repo, id_cliente_valido):
    id_envio = envio_repo.crear(_envio(id_cliente_valido))

    envios = envio_repo.listar_por_cliente(id_cliente_valido)

    assert any(e.id_envio == id_envio for e in envios)


def test_actualizar_modifica_los_campos(envio_repo, id_cliente_valido):
    id_envio = envio_repo.crear(_envio(id_cliente_valido))
    envio = envio_repo.obtener_por_id(id_envio)

    envio.estado = "en_transito"
    envio_repo.actualizar(envio)

    recuperado = envio_repo.obtener_por_id(id_envio)
    assert recuperado.estado == "en_transito"


def test_eliminar_borra_la_fila(envio_repo, id_cliente_valido):
    id_envio = envio_repo.crear(_envio(id_cliente_valido))

    envio_repo.eliminar(id_envio)

    assert envio_repo.obtener_por_id(id_envio) is None
