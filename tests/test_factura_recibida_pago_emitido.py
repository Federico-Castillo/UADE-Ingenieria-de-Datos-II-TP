import pytest

from app.core.exceptions import ValidationError
from app.domain.operador_logistico import OperadorLogistico
from app.domain.proveedor import Proveedor
from app.domain.factura_recibida import FacturaRecibida
from app.domain.pago_emitido import PagoEmitido
from app.services.factura_recibida_service import FacturaRecibidaService

pytestmark = pytest.mark.integration


@pytest.fixture
def id_proveedor_valido(proveedor_repo):
    return proveedor_repo.crear(
        Proveedor(razon_social="TEST_ProveedorFacturacion", cuit="90-60000001-1", email="facturacionprov1@example.com")
    )


@pytest.fixture
def id_operador_valido(operador_logistico_repo):
    return operador_logistico_repo.crear(
        OperadorLogistico(
            razon_social="TEST_OperadorFacturacion", cuit="90-60000002-1", email="facturacionoper1@example.com"
        )
    )


def test_alta_factura_proveedor_crea_cuenta_pagable_del_proveedor(
    factura_recibida_repo, cuenta_corriente_pagable_repo, id_proveedor_valido
):
    factura_recibida_repo.crear(FacturaRecibida(importe_total=1000.0, id_proveedor=id_proveedor_valido))

    cuenta = cuenta_corriente_pagable_repo.obtener_por_proveedor(id_proveedor_valido)

    assert cuenta is not None
    assert cuenta.saldo == 1000.0


def test_alta_factura_operador_crea_cuenta_pagable_del_operador(
    factura_recibida_repo, cuenta_corriente_pagable_repo, id_operador_valido
):
    factura_recibida_repo.crear(
        FacturaRecibida(importe_total=750.0, id_operador_logistico=id_operador_valido)
    )

    cuenta = cuenta_corriente_pagable_repo.obtener_por_operador(id_operador_valido)

    assert cuenta is not None
    assert cuenta.saldo == 750.0


def test_pago_proveedor_descuenta_saldo_y_marca_factura_parcial(
    factura_recibida_repo, pago_emitido_repo, cuenta_corriente_pagable_repo, id_proveedor_valido
):
    id_factura = factura_recibida_repo.crear(
        FacturaRecibida(importe_total=1000.0, id_proveedor=id_proveedor_valido)
    )

    pago_emitido_repo.crear(PagoEmitido(id_factura_recibida=id_factura, monto=300.0, medio_pago="transferencia"))

    cuenta = cuenta_corriente_pagable_repo.obtener_por_proveedor(id_proveedor_valido)
    factura = factura_recibida_repo.obtener_por_id(id_factura)
    assert cuenta.saldo == 700.0
    assert factura.estado == "parcial"


def test_pago_operador_total_marca_factura_pagada(
    factura_recibida_repo, pago_emitido_repo, cuenta_corriente_pagable_repo, id_operador_valido
):
    id_factura = factura_recibida_repo.crear(
        FacturaRecibida(importe_total=500.0, id_operador_logistico=id_operador_valido)
    )

    pago_emitido_repo.crear(PagoEmitido(id_factura_recibida=id_factura, monto=500.0, medio_pago="transferencia"))

    cuenta = cuenta_corriente_pagable_repo.obtener_por_operador(id_operador_valido)
    factura = factura_recibida_repo.obtener_por_id(id_factura)
    assert cuenta.saldo == 0.0
    assert factura.estado == "pagada"


def test_listar_por_proveedor(factura_recibida_repo, id_proveedor_valido):
    id_factura = factura_recibida_repo.crear(
        FacturaRecibida(importe_total=200.0, id_proveedor=id_proveedor_valido)
    )

    facturas = factura_recibida_repo.listar_por_proveedor(id_proveedor_valido)

    assert any(f.id_factura_recibida == id_factura for f in facturas)


def test_listar_por_operador(factura_recibida_repo, id_operador_valido):
    id_factura = factura_recibida_repo.crear(
        FacturaRecibida(importe_total=200.0, id_operador_logistico=id_operador_valido)
    )

    facturas = factura_recibida_repo.listar_por_operador(id_operador_valido)

    assert any(f.id_factura_recibida == id_factura for f in facturas)


def test_service_rechaza_factura_sin_titular(factura_recibida_repo):
    service = FacturaRecibidaService(repository=factura_recibida_repo)

    with pytest.raises(ValidationError):
        service.dar_alta(FacturaRecibida(importe_total=100.0))


def test_service_rechaza_factura_con_ambos_titulares(
    factura_recibida_repo, id_proveedor_valido, id_operador_valido
):
    service = FacturaRecibidaService(repository=factura_recibida_repo)

    with pytest.raises(ValidationError):
        service.dar_alta(
            FacturaRecibida(
                importe_total=100.0,
                id_proveedor=id_proveedor_valido,
                id_operador_logistico=id_operador_valido,
            )
        )
