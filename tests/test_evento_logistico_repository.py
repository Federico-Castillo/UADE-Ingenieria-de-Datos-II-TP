import pytest

from app.domain.cliente import Cliente
from app.domain.envio import Envio
from app.domain.evento_logistico import EventoLogistico

pytestmark = pytest.mark.integration


@pytest.fixture
def id_envio_valido(cliente_repo, envio_repo):
    id_cliente = cliente_repo.crear(
        Cliente(razon_social="TEST_ClienteEvento", cuit="90-70000001-1", email="evento1@example.com")
    )
    return envio_repo.crear(Envio(id_cliente=id_cliente, origen="TEST_Buenos Aires", destino="Rosario"))


def test_crear_y_recuperar_por_id(evento_logistico_repo, id_envio_valido):
    id_evento = evento_logistico_repo.crear(
        EventoLogistico(id_envio=id_envio_valido, tipo_evento="TEST_carga_iniciada")
    )

    recuperado = evento_logistico_repo.obtener_por_id(id_evento)

    assert recuperado is not None
    assert recuperado.id_envio == id_envio_valido
    assert recuperado.tipo_evento == "TEST_carga_iniciada"


def test_listar_por_envio_ordenado(evento_logistico_repo, id_envio_valido):
    id_1 = evento_logistico_repo.crear(EventoLogistico(id_envio=id_envio_valido, tipo_evento="TEST_evento1"))
    id_2 = evento_logistico_repo.crear(EventoLogistico(id_envio=id_envio_valido, tipo_evento="TEST_evento2"))

    eventos = evento_logistico_repo.listar_por_envio(id_envio_valido)
    ids = [e.id_evento for e in eventos]

    assert id_1 in ids
    assert id_2 in ids


def test_ubicacion_se_persiste(evento_logistico_repo, id_envio_valido):
    id_evento = evento_logistico_repo.crear(
        EventoLogistico(
            id_envio=id_envio_valido,
            tipo_evento="TEST_aduana",
            ubicacion={"lat": -34.6, "lon": -58.4, "descripcion": "Puerto de Buenos Aires"},
        )
    )

    recuperado = evento_logistico_repo.obtener_por_id(id_evento)

    assert recuperado.ubicacion["descripcion"] == "Puerto de Buenos Aires"
