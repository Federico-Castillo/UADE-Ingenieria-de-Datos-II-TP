import pytest

from app.domain.cliente import Cliente
from app.domain.factura import Factura
from app.domain.pago import Pago

pytestmark = pytest.mark.integration


@pytest.fixture
def id_cliente_valido(cliente_repo):
    return cliente_repo.crear(
        Cliente(razon_social="TEST_ClienteFacturacion", cuit="90-50000001-1", email="facturacion1@example.com")
    )


def test_alta_factura_crea_cuenta_corriente_con_el_importe(factura_repo, cuenta_corriente_repo, id_cliente_valido):
    factura_repo.crear(Factura(id_cliente=id_cliente_valido, importe_total=1000.0))

    cuenta = cuenta_corriente_repo.obtener_por_cliente(id_cliente_valido)

    assert cuenta is not None
    assert cuenta.saldo == 1000.0


def test_dos_facturas_suman_al_mismo_saldo(factura_repo, cuenta_corriente_repo, id_cliente_valido):
    factura_repo.crear(Factura(id_cliente=id_cliente_valido, importe_total=1000.0))
    factura_repo.crear(Factura(id_cliente=id_cliente_valido, importe_total=500.0))

    cuenta = cuenta_corriente_repo.obtener_por_cliente(id_cliente_valido)

    assert cuenta.saldo == 1500.0


def test_pago_parcial_descuenta_saldo_y_marca_factura_parcial(
    factura_repo, pago_repo, cuenta_corriente_repo, id_cliente_valido
):
    id_factura = factura_repo.crear(Factura(id_cliente=id_cliente_valido, importe_total=1000.0))

    pago_repo.crear(Pago(id_factura=id_factura, monto=400.0, medio_pago="transferencia"))

    cuenta = cuenta_corriente_repo.obtener_por_cliente(id_cliente_valido)
    factura = factura_repo.obtener_por_id(id_factura)
    assert cuenta.saldo == 600.0
    assert factura.estado == "parcial"


def test_pago_total_marca_factura_pagada(factura_repo, pago_repo, cuenta_corriente_repo, id_cliente_valido):
    id_factura = factura_repo.crear(Factura(id_cliente=id_cliente_valido, importe_total=1000.0))

    pago_repo.crear(Pago(id_factura=id_factura, monto=1000.0, medio_pago="transferencia"))

    cuenta = cuenta_corriente_repo.obtener_por_cliente(id_cliente_valido)
    factura = factura_repo.obtener_por_id(id_factura)
    assert cuenta.saldo == 0.0
    assert factura.estado == "pagada"


def test_listar_por_cliente(factura_repo, id_cliente_valido):
    id_factura = factura_repo.crear(Factura(id_cliente=id_cliente_valido, importe_total=200.0))

    facturas = factura_repo.listar_por_cliente(id_cliente_valido)

    assert any(f.id_factura == id_factura for f in facturas)


def test_listar_pagos_por_factura(factura_repo, pago_repo, id_cliente_valido):
    id_factura = factura_repo.crear(Factura(id_cliente=id_cliente_valido, importe_total=300.0))
    id_pago = pago_repo.crear(Pago(id_factura=id_factura, monto=100.0, medio_pago="efectivo"))

    pagos = pago_repo.listar_por_factura(id_factura)

    assert any(p.id_pago == id_pago for p in pagos)
