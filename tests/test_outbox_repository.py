import pytest

from app.domain.cliente import Cliente
from app.domain.envio import Envio

pytestmark = pytest.mark.integration

_MAX_INTENTOS = 5


@pytest.fixture
def id_cliente_valido(cliente_repo):
    return cliente_repo.crear(
        Cliente(razon_social="TEST_ClienteOutbox", cuit="90-96000001-1", email="outbox1@example.com")
    )


def test_alta_de_cliente_encola_un_evento_pendiente(outbox_repo, id_cliente_valido):
    pendientes = outbox_repo.listar_pendientes(limite=1000)

    fila = next(e for e in pendientes if e.entidad == "cliente" and e.id_entidad == id_cliente_valido)

    assert fila.tipo_evento == "creado"
    assert fila.payload == {"id_cliente": id_cliente_valido, "razon_social": "TEST_ClienteOutbox"}
    assert fila.estado == "pendiente"
    assert fila.intentos == 0


def test_alta_de_envio_encola_un_evento_con_el_payload_esperado(outbox_repo, envio_repo, id_cliente_valido):
    id_envio = envio_repo.crear(
        Envio(id_cliente=id_cliente_valido, origen="TEST_A", destino="TEST_B", estado="pendiente")
    )

    pendientes = outbox_repo.listar_pendientes(limite=1000)
    fila = next(e for e in pendientes if e.entidad == "envio" and e.id_entidad == id_envio)

    assert fila.tipo_evento == "creado"
    assert fila.payload == {
        "id_envio": id_envio, "id_cliente": id_cliente_valido, "estado": "pendiente", "prioridad": "normal",
    }


def test_marcar_procesado_saca_el_evento_de_pendientes(outbox_repo, id_cliente_valido):
    pendientes = outbox_repo.listar_pendientes(limite=1000)
    fila = next(e for e in pendientes if e.entidad == "cliente" and e.id_entidad == id_cliente_valido)

    outbox_repo.marcar_procesado(fila.id_evento)

    pendientes_despues = outbox_repo.listar_pendientes(limite=1000)
    assert not any(e.id_evento == fila.id_evento for e in pendientes_despues)


def test_marcar_fallo_repetido_pasa_a_dead_letter(outbox_repo, id_cliente_valido):
    pendientes = outbox_repo.listar_pendientes(limite=1000)
    fila = next(e for e in pendientes if e.entidad == "cliente" and e.id_entidad == id_cliente_valido)

    for _ in range(_MAX_INTENTOS - 1):
        outbox_repo.marcar_fallo(fila.id_evento, max_intentos=_MAX_INTENTOS)
    # todavía no llegó al máximo
    assert not any(e.id_evento == fila.id_evento for e in outbox_repo.listar_dead_letter())

    outbox_repo.marcar_fallo(fila.id_evento, max_intentos=_MAX_INTENTOS)

    dead_letter = outbox_repo.listar_dead_letter()
    encontrada = next(e for e in dead_letter if e.id_evento == fila.id_evento)
    assert encontrada.intentos == _MAX_INTENTOS


def test_reintentar_vuelve_a_pendiente_y_resetea_intentos(outbox_repo, id_cliente_valido):
    pendientes = outbox_repo.listar_pendientes(limite=1000)
    fila = next(e for e in pendientes if e.entidad == "cliente" and e.id_entidad == id_cliente_valido)
    for _ in range(_MAX_INTENTOS):
        outbox_repo.marcar_fallo(fila.id_evento, max_intentos=_MAX_INTENTOS)

    reintentado = outbox_repo.reintentar(fila.id_evento)

    assert reintentado is True
    pendientes_despues = outbox_repo.listar_pendientes(limite=1000)
    encontrada = next(e for e in pendientes_despues if e.id_evento == fila.id_evento)
    assert encontrada.intentos == 0


def test_reintentar_evento_inexistente_devuelve_false(outbox_repo):
    assert outbox_repo.reintentar("no-existe") is False
