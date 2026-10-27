from datetime import timedelta

import pytest

from app.domain.cliente import Cliente
from app.domain.envio import Envio
from app.domain.evento_logistico import EventoLogistico
from app.domain.incidente import Incidente
from app.domain.prediccion_riesgo import PrediccionRiesgo
from app.repositories.prediccion_riesgo_repository import PrediccionRiesgoRepository
from app.services.evento_logistico_service import EventoLogisticoService
from app.services.incidente_service import IncidenteService
from app.services.reporte_operativo_service import ReporteOperativoService

pytestmark = pytest.mark.integration


@pytest.fixture
def id_cliente_valido(cliente_repo):
    return cliente_repo.crear(
        Cliente(
            razon_social="TEST_ClienteReporteOp",
            cuit="90-95000001-1",
            email="reporteop1@example.com",
            pais="TEST_PaisReporteOp",
        )
    )


@pytest.fixture
def service():
    return ReporteOperativoService()


def test_envios_por_pais_cuenta_los_del_pais_de_prueba(service, envio_repo, id_cliente_valido):
    envio_repo.crear(Envio(id_cliente=id_cliente_valido, origen="TEST_A", destino="TEST_B"))
    envio_repo.crear(Envio(id_cliente=id_cliente_valido, origen="TEST_C", destino="TEST_D"))

    fila = next(f for f in service.envios_por_pais() if f["pais"] == "TEST_PaisReporteOp")

    assert fila["cantidad"] == 2


def test_envios_por_cliente_cuenta_los_del_cliente(service, envio_repo, id_cliente_valido):
    envio_repo.crear(Envio(id_cliente=id_cliente_valido, origen="TEST_A", destino="TEST_B"))

    fila = next(f for f in service.envios_por_cliente() if f["id_cliente"] == id_cliente_valido)

    assert fila["cantidad"] == 1
    assert fila["razon_social"] == "TEST_ClienteReporteOp"


def test_envios_por_estado_delta(service, envio_repo, id_cliente_valido):
    antes = dict((f["estado"], f["cantidad"]) for f in service.envios_por_estado())

    envio_repo.crear(Envio(id_cliente=id_cliente_valido, origen="TEST_A", destino="TEST_B", estado="demorado"))
    envio_repo.crear(Envio(id_cliente=id_cliente_valido, origen="TEST_C", destino="TEST_D", estado="demorado"))

    despues = dict((f["estado"], f["cantidad"]) for f in service.envios_por_estado())

    assert despues["demorado"] - antes.get("demorado", 0) == 2


def test_envios_demorados_incluye_el_creado(service, envio_repo, id_cliente_valido):
    id_envio = envio_repo.crear(
        Envio(id_cliente=id_cliente_valido, origen="TEST_X", destino="TEST_Y", estado="demorado")
    )

    assert any(e.id_envio == id_envio for e in service.envios_demorados())


def test_incidentes_abiertos_incluye_el_creado(service, envio_repo, id_cliente_valido):
    id_envio = envio_repo.crear(Envio(id_cliente=id_cliente_valido, origen="TEST_A", destino="TEST_B"))
    incidente = IncidenteService().registrar(
        Incidente(id_envio=id_envio, tipo="TEST_incidente_abierto", severidad="baja")
    )

    assert any(i.id_incidente == incidente.id_incidente for i in service.incidentes_abiertos())


def test_tiempos_envio_por_cliente_calcula_horas(service, envio_repo, id_cliente_valido):
    id_envio = envio_repo.crear(
        Envio(id_cliente=id_cliente_valido, origen="TEST_A", destino="TEST_B", estado="entregado")
    )
    envio = envio_repo.obtener_por_id(id_envio)
    EventoLogisticoService().registrar(
        EventoLogistico(
            id_envio=id_envio,
            tipo_evento="entregado",
            descripcion="TEST_evento_entrega_reporte",
            fecha_hora=envio.fecha_creacion + timedelta(hours=5),
        )
    )

    fila = next(f for f in service.tiempos_envio_por_cliente() if f["id_cliente"] == id_cliente_valido)

    assert fila["cantidad_envios"] == 1
    assert fila["horas_min"] == pytest.approx(5.0, abs=0.01)
    assert fila["horas_max"] == pytest.approx(5.0, abs=0.01)
    assert fila["horas_promedio"] == pytest.approx(5.0, abs=0.01)


def test_incidentes_promedio_por_cliente(service, envio_repo, id_cliente_valido):
    id_envio1 = envio_repo.crear(Envio(id_cliente=id_cliente_valido, origen="TEST_A", destino="TEST_B"))
    envio_repo.crear(Envio(id_cliente=id_cliente_valido, origen="TEST_C", destino="TEST_D"))
    IncidenteService().registrar(Incidente(id_envio=id_envio1, tipo="TEST_incidente_prom", severidad="baja"))

    fila = next(f for f in service.incidentes_promedio_por_cliente() if f["grupo"] == id_cliente_valido)

    assert fila["cantidad_envios"] == 2
    assert fila["cantidad_incidentes"] == 1
    assert fila["promedio_por_envio"] == pytest.approx(0.5)


def test_analisis_predictivo_detecta_riesgo_alto(service, envio_repo, id_cliente_valido, predicciones_creadas):
    id_envio = envio_repo.crear(Envio(id_cliente=id_cliente_valido, origen="TEST_A", destino="TEST_B"))
    id_prediccion = PrediccionRiesgoRepository().crear(
        PrediccionRiesgo(id_envio=id_envio, probabilidad_demora=0.95)
    )
    predicciones_creadas.append(id_prediccion)

    resultado = service.analisis_predictivo_riesgos()

    assert any(r["id_envio"] == id_envio for r in resultado["envios_riesgo_alto"])
