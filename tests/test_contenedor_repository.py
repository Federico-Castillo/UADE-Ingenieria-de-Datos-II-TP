import pytest

from app.core.exceptions import DuplicateError
from app.domain.contenedor import Contenedor

pytestmark = pytest.mark.integration


def _contenedor(codigo: str, **kwargs) -> Contenedor:
    defaults = dict(tipo="reefer", capacidad=20.5, estado="disponible")
    defaults.update(kwargs)
    return Contenedor(codigo_internacional=f"{codigo}", **defaults)


def test_crear_y_recuperar_por_id(contenedor_repo):
    id_contenedor = contenedor_repo.crear(_contenedor("TEST_CONT001"))

    recuperado = contenedor_repo.obtener_por_id(id_contenedor)

    assert recuperado is not None
    assert recuperado.codigo_internacional == "TEST_CONT001"
    assert recuperado.capacidad == 20.5


def test_codigo_duplicado_lanza_duplicate_error(contenedor_repo):
    contenedor_repo.crear(_contenedor("TEST_CONT002"))

    with pytest.raises(DuplicateError):
        contenedor_repo.crear(_contenedor("TEST_CONT002"))


def test_actualizar_modifica_los_campos(contenedor_repo):
    id_contenedor = contenedor_repo.crear(_contenedor("TEST_CONT003"))
    contenedor = contenedor_repo.obtener_por_id(id_contenedor)

    contenedor.estado = "en_uso"
    contenedor_repo.actualizar(contenedor)

    recuperado = contenedor_repo.obtener_por_id(id_contenedor)
    assert recuperado.estado == "en_uso"


def test_eliminar_borra_la_fila(contenedor_repo):
    id_contenedor = contenedor_repo.crear(_contenedor("TEST_CONT004"))

    contenedor_repo.eliminar(id_contenedor)

    assert contenedor_repo.obtener_por_id(id_contenedor) is None
