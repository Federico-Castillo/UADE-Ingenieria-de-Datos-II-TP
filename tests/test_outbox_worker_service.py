import pytest

from app.db.neo4j_driver import session as neo4j_session
from app.domain.cliente import Cliente
from app.domain.envio import Envio
from app.services.outbox_worker_service import OutboxWorkerService

pytestmark = pytest.mark.integration


@pytest.fixture
def id_cliente_valido(cliente_repo):
    return cliente_repo.crear(
        Cliente(razon_social="TEST_ClienteOutboxWorker", cuit="90-97000001-1", email="outboxworker1@example.com")
    )


def _nodo_cliente(id_cliente: int) -> dict | None:
    with neo4j_session() as sess:
        record = sess.run("MATCH (c:Cliente {id_cliente: $id}) RETURN c", id=id_cliente).single()
        return dict(record["c"]) if record else None


def _nodo_envio(id_envio: int) -> dict | None:
    with neo4j_session() as sess:
        record = sess.run("MATCH (e:Envio {id_envio: $id}) RETURN e", id=id_envio).single()
        return dict(record["e"]) if record else None


def _existe_relacion_solicita(id_cliente: int, id_envio: int) -> bool:
    with neo4j_session() as sess:
        record = sess.run(
            "MATCH (c:Cliente {id_cliente: $id_cliente})-[:SOLICITA]->(e:Envio {id_envio: $id_envio}) RETURN c",
            id_cliente=id_cliente, id_envio=id_envio,
        ).single()
        return record is not None


def test_procesar_pendientes_proyecta_cliente_en_neo4j(id_cliente_valido):
    resultado = OutboxWorkerService().procesar_pendientes()

    assert resultado["procesados"] >= 1
    nodo = _nodo_cliente(id_cliente_valido)
    assert nodo is not None
    assert nodo["razon_social"] == "TEST_ClienteOutboxWorker"


def test_procesar_pendientes_proyecta_envio_y_relacion_solicita(envio_repo, id_cliente_valido):
    id_envio = envio_repo.crear(
        Envio(id_cliente=id_cliente_valido, origen="TEST_A", destino="TEST_B", estado="pendiente")
    )

    OutboxWorkerService().procesar_pendientes()

    nodo = _nodo_envio(id_envio)
    assert nodo is not None
    assert nodo["estado"] == "pendiente"
    assert nodo["prioridad"] == "normal"
    assert _existe_relacion_solicita(id_cliente_valido, id_envio)


def test_actualizar_envio_propaga_el_nuevo_estado(envio_repo, id_cliente_valido):
    id_envio = envio_repo.crear(Envio(id_cliente=id_cliente_valido, origen="TEST_A", destino="TEST_B"))
    OutboxWorkerService().procesar_pendientes()

    envio = envio_repo.obtener_por_id(id_envio)
    envio.estado = "entregado"
    envio_repo.actualizar(envio)
    OutboxWorkerService().procesar_pendientes()

    nodo = _nodo_envio(id_envio)
    assert nodo["estado"] == "entregado"


def test_eliminar_envio_borra_el_nodo_en_neo4j(envio_repo, id_cliente_valido):
    id_envio = envio_repo.crear(Envio(id_cliente=id_cliente_valido, origen="TEST_A", destino="TEST_B"))
    OutboxWorkerService().procesar_pendientes()
    assert _nodo_envio(id_envio) is not None

    envio_repo.eliminar(id_envio)
    OutboxWorkerService().procesar_pendientes()

    assert _nodo_envio(id_envio) is None


def test_procesar_pendientes_es_idempotente_si_no_hay_nada_nuevo(id_cliente_valido):
    OutboxWorkerService().procesar_pendientes()

    resultado = OutboxWorkerService().procesar_pendientes()

    assert resultado == {"procesados": 0, "fallidos": 0, "total": 0}


def test_reintentar_evento_inexistente_lanza_not_found():
    from app.core.exceptions import NotFoundError

    with pytest.raises(NotFoundError):
        OutboxWorkerService().reintentar("no-existe")
