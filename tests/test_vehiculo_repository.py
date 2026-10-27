import pytest

from app.core.exceptions import DuplicateError
from app.domain.vehiculo import Vehiculo

pytestmark = pytest.mark.integration


def _vehiculo(identificacion: str, **kwargs) -> Vehiculo:
    defaults = dict(tipo="camion", empresa_operadora="TEST_Transportes")
    defaults.update(kwargs)
    return Vehiculo(identificacion=identificacion, **defaults)


def test_crear_y_recuperar_por_id(vehiculo_repo):
    id_vehiculo = vehiculo_repo.crear(_vehiculo("TEST_ABC123"))

    recuperado = vehiculo_repo.obtener_por_id(id_vehiculo)

    assert recuperado is not None
    assert recuperado.identificacion == "TEST_ABC123"


def test_identificacion_duplicada_lanza_duplicate_error(vehiculo_repo):
    vehiculo_repo.crear(_vehiculo("TEST_DEF456"))

    with pytest.raises(DuplicateError):
        vehiculo_repo.crear(_vehiculo("TEST_DEF456"))


def test_eliminar_borra_la_fila(vehiculo_repo):
    id_vehiculo = vehiculo_repo.crear(_vehiculo("TEST_GHI789"))

    vehiculo_repo.eliminar(id_vehiculo)

    assert vehiculo_repo.obtener_por_id(id_vehiculo) is None
