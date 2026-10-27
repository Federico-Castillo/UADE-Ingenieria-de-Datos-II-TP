import pytest

from app.core.exceptions import DuplicateError
from app.domain.operador_logistico import OperadorLogistico

pytestmark = pytest.mark.integration


def _operador(razon_social: str, cuit: str, email: str, **kwargs) -> OperadorLogistico:
    return OperadorLogistico(razon_social=f"TEST_{razon_social}", cuit=cuit, email=email, **kwargs)


def test_crear_y_recuperar_por_id(operador_logistico_repo):
    id_operador = operador_logistico_repo.crear(
        _operador("Transportes SA", "90-30000001-1", "op1@example.com")
    )

    recuperado = operador_logistico_repo.obtener_por_id(id_operador)

    assert recuperado is not None
    assert recuperado.razon_social == "TEST_Transportes SA"
    assert recuperado.estado == "activo"


def test_cuit_duplicado_lanza_duplicate_error(operador_logistico_repo):
    operador_logistico_repo.crear(_operador("A", "90-30000002-1", "op2a@example.com"))

    with pytest.raises(DuplicateError):
        operador_logistico_repo.crear(_operador("B", "90-30000002-1", "op2b@example.com"))


def test_baja_logica_no_borra_la_fila(operador_logistico_repo):
    id_operador = operador_logistico_repo.crear(_operador("ParaBaja", "90-30000003-1", "op3@example.com"))

    operador_logistico_repo.eliminar(id_operador)

    recuperado = operador_logistico_repo.obtener_por_id(id_operador)
    assert recuperado is not None
    assert recuperado.estado == "inactivo"
