import pytest

from app.core.exceptions import DuplicateError
from app.domain.proveedor import Proveedor

pytestmark = pytest.mark.integration


def _proveedor(razon_social: str, cuit: str, email: str, **kwargs) -> Proveedor:
    return Proveedor(razon_social=f"TEST_{razon_social}", cuit=cuit, email=email, **kwargs)


def test_crear_y_recuperar_por_id(proveedor_repo):
    id_proveedor = proveedor_repo.crear(_proveedor("Insumos SA", "90-20000001-1", "prov1@example.com"))

    recuperado = proveedor_repo.obtener_por_id(id_proveedor)

    assert recuperado is not None
    assert recuperado.razon_social == "TEST_Insumos SA"
    assert recuperado.estado == "activo"


def test_cuit_duplicado_lanza_duplicate_error(proveedor_repo):
    proveedor_repo.crear(_proveedor("A", "90-20000002-1", "prov2a@example.com"))

    with pytest.raises(DuplicateError):
        proveedor_repo.crear(_proveedor("B", "90-20000002-1", "prov2b@example.com"))


def test_baja_logica_no_borra_la_fila(proveedor_repo):
    id_proveedor = proveedor_repo.crear(_proveedor("ParaBaja", "90-20000003-1", "prov3@example.com"))

    proveedor_repo.eliminar(id_proveedor)

    recuperado = proveedor_repo.obtener_por_id(id_proveedor)
    assert recuperado is not None
    assert recuperado.estado == "inactivo"


def test_buscar_matchea_texto_parcial(proveedor_repo):
    proveedor_repo.crear(_proveedor("Repuestos del Norte", "90-20000004-1", "prov4@example.com"))

    resultados = proveedor_repo.buscar("Repuestos")

    assert any(p.razon_social == "TEST_Repuestos del Norte" for p in resultados)
