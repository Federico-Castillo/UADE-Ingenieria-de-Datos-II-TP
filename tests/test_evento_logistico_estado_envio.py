import pytest

from app.core.exceptions import TransaccionCrossEngineError
from app.domain.cliente import Cliente
from app.domain.envio import Envio
from app.domain.evento_logistico import EventoLogistico
from app.services.evento_logistico_service import EventoLogisticoService, estado_tras_evento


@pytest.mark.parametrize(
    "estado, tipo_evento, esperado",
    [
        ("pendiente", "carga_iniciada", "en_transito"),
        ("pendiente", "salida_origen", "en_transito"),
        ("pendiente", "entregado", "entregado"),
        ("en_transito", "entregado", "entregado"),
        ("en_transito", "carga_iniciada", "en_transito"),
        ("demorado", "entregado", "demorado"),  # sigue 'demorado': es la etiqueta de "llegó tarde"
        ("cancelado", "carga_iniciada", "cancelado"),
        ("cancelado", "entregado", "cancelado"),
        ("entregado", "carga_iniciada", "entregado"),  # un evento tardío no lo retrocede
        ("pendiente", "aduana", "pendiente"),  # tipos informativos no cambian el estado
    ],
)
def test_transiciones_de_estado(estado, tipo_evento, esperado):
    assert estado_tras_evento(estado, tipo_evento) == esperado


@pytest.fixture
def id_envio_pendiente(cliente_repo, envio_repo):
    id_cliente = cliente_repo.crear(
        Cliente(razon_social="TEST_ClienteEstadoEvento", cuit="90-70000044-1", email="estado.evento@example.com")
    )
    return envio_repo.crear(Envio(id_cliente=id_cliente, origen="TEST_Rosario", destino="Lima"))


@pytest.mark.integration
def test_registrar_evento_actualiza_el_estado_del_envio(id_envio_pendiente, envio_repo):
    service = EventoLogisticoService()

    service.registrar(EventoLogistico(id_envio=id_envio_pendiente, tipo_evento="carga_iniciada", descripcion="TEST_carga"))
    assert envio_repo.obtener_por_id(id_envio_pendiente).estado == "en_transito"

    service.registrar(EventoLogistico(id_envio=id_envio_pendiente, tipo_evento="entregado", descripcion="TEST_entrega"))
    assert envio_repo.obtener_por_id(id_envio_pendiente).estado == "entregado"


@pytest.mark.integration
def test_si_falla_la_actualizacion_del_envio_se_revierte_el_evento(id_envio_pendiente, envio_repo, evento_logistico_repo):
    from app.core.exceptions import RepositoryError

    class EnvioRepoQueFalla:
        def obtener_por_id(self, id_envio):
            return envio_repo.obtener_por_id(id_envio)

        def actualizar(self, envio):
            raise RepositoryError("falla simulada")

    service = EventoLogisticoService(envio_repository=EnvioRepoQueFalla())

    with pytest.raises(TransaccionCrossEngineError):
        service.registrar(EventoLogistico(id_envio=id_envio_pendiente, tipo_evento="carga_iniciada", descripcion="TEST_carga"))

    assert evento_logistico_repo.listar_por_envio(id_envio_pendiente) == []
    assert envio_repo.obtener_por_id(id_envio_pendiente).estado == "pendiente"


@pytest.mark.integration
def test_sincronizar_corrige_envios_con_eventos_ya_cargados(id_envio_pendiente, envio_repo, evento_logistico_repo):
    # evento cargado "a mano" en el repo (como antes de existir la regla): el estado quedó desfasado
    evento_logistico_repo.crear(
        EventoLogistico(id_envio=id_envio_pendiente, tipo_evento="carga_iniciada", descripcion="TEST_carga")
    )
    assert envio_repo.obtener_por_id(id_envio_pendiente).estado == "pendiente"

    cambios = EventoLogisticoService().sincronizar_estados_envios()

    assert {"id_envio": id_envio_pendiente, "antes": "pendiente", "despues": "en_transito"} in cambios
    assert envio_repo.obtener_por_id(id_envio_pendiente).estado == "en_transito"
