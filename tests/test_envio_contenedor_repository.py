import pytest

from app.core.exceptions import DuplicateError
from app.domain.cliente import Cliente
from app.domain.contenedor import Contenedor
from app.domain.envio import Envio

pytestmark = pytest.mark.integration


@pytest.fixture
def contexto(cliente_repo, envio_repo, contenedor_repo):
    id_cliente = cliente_repo.crear(
        Cliente(razon_social="TEST_ClienteEnvioCont", cuit="90-90000001-1", email="enviocont1@example.com")
    )
    id_envio = envio_repo.crear(Envio(id_cliente=id_cliente, origen="TEST_Rosario", destino="Mendoza"))
    id_contenedor = contenedor_repo.crear(
        Contenedor(codigo_internacional="TEST_ENVCONT001", tipo="dry", capacidad=10.0)
    )
    return id_envio, id_contenedor


def test_asignar_y_listar_contenedores_de_envio(envio_contenedor_repo, contexto):
    id_envio, id_contenedor = contexto

    envio_contenedor_repo.asignar(id_envio, id_contenedor)

    contenedores = envio_contenedor_repo.listar_contenedores_de_envio(id_envio)
    assert any(c.id_contenedor == id_contenedor for c in contenedores)


def test_asignar_duplicado_lanza_duplicate_error(envio_contenedor_repo, contexto):
    id_envio, id_contenedor = contexto
    envio_contenedor_repo.asignar(id_envio, id_contenedor)

    with pytest.raises(DuplicateError):
        envio_contenedor_repo.asignar(id_envio, id_contenedor)


def test_envio_actual_de_contenedor(envio_contenedor_repo, contexto):
    id_envio, id_contenedor = contexto
    envio_contenedor_repo.asignar(id_envio, id_contenedor)

    assert envio_contenedor_repo.envio_actual_de_contenedor(id_contenedor) == id_envio


def test_quitar_contenedor(envio_contenedor_repo, contexto):
    id_envio, id_contenedor = contexto
    envio_contenedor_repo.asignar(id_envio, id_contenedor)

    assert envio_contenedor_repo.quitar(id_envio, id_contenedor) is True
    assert envio_contenedor_repo.listar_contenedores_de_envio(id_envio) == []


def test_quitar_inexistente_devuelve_false(envio_contenedor_repo, contexto):
    id_envio, id_contenedor = contexto
    assert envio_contenedor_repo.quitar(id_envio, id_contenedor) is False
