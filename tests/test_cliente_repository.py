import pytest

from app.core.exceptions import DuplicateError
from app.domain.cliente import Cliente

pytestmark = pytest.mark.integration


def _cliente(razon_social: str, cuit: str, email: str, **kwargs) -> Cliente:
    return Cliente(
        razon_social=f"TEST_{razon_social}",
        cuit=cuit,
        email=email,
        **kwargs,
    )


def test_crear_y_recuperar_por_id(cliente_repo):
    cliente = _cliente("Acme", "90-10000001-1", "test1@example.com")
    id_cliente = cliente_repo.crear(cliente)

    recuperado = cliente_repo.obtener_por_id(id_cliente)

    assert recuperado is not None
    assert recuperado.razon_social == "TEST_Acme"
    assert recuperado.cuit == "90-10000001-1"
    assert recuperado.estado == "activo"


def test_cuit_duplicado_lanza_duplicate_error(cliente_repo):
    cliente_repo.crear(_cliente("Acme", "90-10000002-1", "test2a@example.com"))

    with pytest.raises(DuplicateError):
        cliente_repo.crear(_cliente("Otra", "90-10000002-1", "test2b@example.com"))


def test_listar_solo_activos_excluye_inactivos(cliente_repo):
    id_activo = cliente_repo.crear(_cliente("Activo", "90-10000003-1", "test3a@example.com"))
    id_inactivo = cliente_repo.crear(_cliente("Inactivo", "90-10000004-1", "test3b@example.com"))
    cliente_repo.eliminar(id_inactivo)

    activos = cliente_repo.listar(solo_activos=True)
    ids_activos = {c.id_cliente for c in activos}

    assert id_activo in ids_activos
    assert id_inactivo not in ids_activos


def test_baja_logica_no_borra_la_fila(cliente_repo):
    id_cliente = cliente_repo.crear(_cliente("ParaBaja", "90-10000005-1", "test4@example.com"))

    cliente_repo.eliminar(id_cliente)

    recuperado = cliente_repo.obtener_por_id(id_cliente)
    assert recuperado is not None
    assert recuperado.estado == "inactivo"


def test_actualizar_modifica_los_campos(cliente_repo):
    id_cliente = cliente_repo.crear(_cliente("Original", "90-10000006-1", "test5@example.com"))
    cliente = cliente_repo.obtener_por_id(id_cliente)

    cliente.razon_social = "TEST_Modificado"
    cliente.telefono = "11-5555-5555"
    cliente_repo.actualizar(cliente)

    recuperado = cliente_repo.obtener_por_id(id_cliente)
    assert recuperado.razon_social == "TEST_Modificado"
    assert recuperado.telefono == "11-5555-5555"


def test_buscar_matchea_texto_parcial(cliente_repo):
    cliente_repo.crear(_cliente("Logistica del Sur", "90-10000007-1", "test6@example.com"))

    resultados = cliente_repo.buscar("Logistica")

    assert any(c.razon_social == "TEST_Logistica del Sur" for c in resultados)
