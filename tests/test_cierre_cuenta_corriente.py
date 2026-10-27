import pytest

from app.core.exceptions import ValidationError
from app.domain.cliente import Cliente
from app.domain.factura import Factura
from app.domain.factura_recibida import FacturaRecibida
from app.domain.proveedor import Proveedor
from app.services.cierre_cuenta_corriente_service import CierreCuentaCorrienteService

pytestmark = pytest.mark.integration

_PERIODO = "2026-01"
_OTRO_PERIODO = "2026-02"


@pytest.fixture
def id_cliente_valido(cliente_repo):
    return cliente_repo.crear(
        Cliente(razon_social="TEST_ClienteCierre", cuit="90-70000001-1", email="cierre1@example.com")
    )


@pytest.fixture
def id_proveedor_valido(proveedor_repo):
    return proveedor_repo.crear(
        Proveedor(razon_social="TEST_ProveedorCierre", cuit="90-70000002-1", email="cierreprov1@example.com")
    )


@pytest.fixture
def service():
    return CierreCuentaCorrienteService()


def test_ejecutar_cierre_registra_snapshot_del_saldo_vivo(
    service, factura_repo, id_cliente_valido
):
    factura_repo.crear(Factura(id_cliente=id_cliente_valido, importe_total=1000.0))

    resultado = service.ejecutar_cierre_mensual(_PERIODO)

    assert resultado["periodo"] == _PERIODO
    assert resultado["clientes_cerrados"] >= 1
    historial = service.historial_cliente(id_cliente_valido)
    assert len(historial) == 1
    assert historial[0].periodo == _PERIODO
    assert historial[0].saldo_al_cierre == 1000.0


def test_reejecutar_el_mismo_periodo_actualiza_en_vez_de_duplicar(
    service, factura_repo, id_cliente_valido
):
    factura_repo.crear(Factura(id_cliente=id_cliente_valido, importe_total=1000.0))
    service.ejecutar_cierre_mensual(_PERIODO)

    factura_repo.crear(Factura(id_cliente=id_cliente_valido, importe_total=500.0))
    service.ejecutar_cierre_mensual(_PERIODO)

    historial = service.historial_cliente(id_cliente_valido)
    assert len(historial) == 1
    assert historial[0].saldo_al_cierre == 1500.0


def test_dos_periodos_distintos_generan_dos_snapshots(
    service, factura_repo, id_cliente_valido
):
    factura_repo.crear(Factura(id_cliente=id_cliente_valido, importe_total=1000.0))
    service.ejecutar_cierre_mensual(_PERIODO)

    factura_repo.crear(Factura(id_cliente=id_cliente_valido, importe_total=200.0))
    service.ejecutar_cierre_mensual(_OTRO_PERIODO)

    historial = service.historial_cliente(id_cliente_valido)
    assert len(historial) == 2
    periodos = {c.periodo for c in historial}
    assert periodos == {_PERIODO, _OTRO_PERIODO}


def test_cierre_tambien_cubre_cuentas_pagables_de_proveedores(
    service, factura_recibida_repo, id_proveedor_valido
):
    factura_recibida_repo.crear(FacturaRecibida(importe_total=800.0, id_proveedor=id_proveedor_valido))

    service.ejecutar_cierre_mensual(_PERIODO)

    historial = service.historial_proveedor(id_proveedor_valido)
    assert len(historial) == 1
    assert historial[0].saldo_al_cierre == 800.0


def test_periodo_con_formato_invalido_lanza_validation_error(service):
    with pytest.raises(ValidationError):
        service.ejecutar_cierre_mensual("2026-13")
    with pytest.raises(ValidationError):
        service.ejecutar_cierre_mensual("26-01")


def test_historial_periodo_incluye_clientes_y_pagables(
    service, factura_repo, factura_recibida_repo, id_cliente_valido, id_proveedor_valido
):
    factura_repo.crear(Factura(id_cliente=id_cliente_valido, importe_total=100.0))
    factura_recibida_repo.crear(FacturaRecibida(importe_total=50.0, id_proveedor=id_proveedor_valido))

    service.ejecutar_cierre_mensual(_PERIODO)
    resultado = service.historial_periodo(_PERIODO)

    assert any(c.id_cliente == id_cliente_valido for c in resultado["clientes"])
    assert any(c.id_proveedor == id_proveedor_valido for c in resultado["pagables"])
