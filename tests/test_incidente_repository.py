import pytest

from app.domain.cliente import Cliente
from app.domain.envio import Envio
from app.domain.incidente import Incidente

pytestmark = pytest.mark.integration


@pytest.fixture
def id_envio_valido(cliente_repo, envio_repo):
    id_cliente = cliente_repo.crear(
        Cliente(razon_social="TEST_ClienteIncidente", cuit="90-70000002-1", email="incidente1@example.com")
    )
    return envio_repo.crear(Envio(id_cliente=id_cliente, origen="TEST_Mendoza", destino="Cordoba"))


def test_crear_y_recuperar_por_id(incidente_repo, id_envio_valido):
    id_incidente = incidente_repo.crear(
        Incidente(id_envio=id_envio_valido, tipo="TEST_demora_aduanera", severidad="alta")
    )

    recuperado = incidente_repo.obtener_por_id(id_incidente)

    assert recuperado is not None
    assert recuperado.estado == "abierto"
    assert recuperado.severidad == "alta"


def test_cambiar_estado(incidente_repo, id_envio_valido):
    id_incidente = incidente_repo.crear(
        Incidente(id_envio=id_envio_valido, tipo="TEST_rotura", severidad="media")
    )

    actualizado = incidente_repo.actualizar_estado(id_incidente, "cerrado")

    assert actualizado is True
    assert incidente_repo.obtener_por_id(id_incidente).estado == "cerrado"


def test_listar_solo_abiertos(incidente_repo, id_envio_valido):
    id_abierto = incidente_repo.crear(Incidente(id_envio=id_envio_valido, tipo="TEST_abierto1", severidad="baja"))
    id_cerrado = incidente_repo.crear(Incidente(id_envio=id_envio_valido, tipo="TEST_cerrado1", severidad="baja"))
    incidente_repo.actualizar_estado(id_cerrado, "cerrado")

    abiertos = incidente_repo.listar(solo_abiertos=True)
    ids_abiertos = {i.id_incidente for i in abiertos}

    assert id_abierto in ids_abiertos
    assert id_cerrado not in ids_abiertos
