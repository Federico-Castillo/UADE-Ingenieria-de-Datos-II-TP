import pytest

from app.domain.grupo_trabajo import GrupoTrabajo

pytestmark = pytest.mark.integration


def test_crear_y_recuperar_por_id(grupo_trabajo_repo):
    id_grupo = grupo_trabajo_repo.crear(GrupoTrabajo(nombre="TEST_Operaciones", integrantes=[1, 2]))

    recuperado = grupo_trabajo_repo.obtener_por_id(id_grupo)

    assert recuperado is not None
    assert recuperado.nombre == "TEST_Operaciones"
    assert recuperado.integrantes == [1, 2]


def test_agregar_y_quitar_integrante(grupo_trabajo_repo):
    id_grupo = grupo_trabajo_repo.crear(GrupoTrabajo(nombre="TEST_Soporte", integrantes=[]))

    assert grupo_trabajo_repo.agregar_integrante(id_grupo, 5) is True
    assert 5 in grupo_trabajo_repo.obtener_por_id(id_grupo).integrantes

    assert grupo_trabajo_repo.quitar_integrante(id_grupo, 5) is True
    assert 5 not in grupo_trabajo_repo.obtener_por_id(id_grupo).integrantes


def test_eliminar(grupo_trabajo_repo):
    id_grupo = grupo_trabajo_repo.crear(GrupoTrabajo(nombre="TEST_ParaBorrar"))

    assert grupo_trabajo_repo.eliminar(id_grupo) is True
    assert grupo_trabajo_repo.obtener_por_id(id_grupo) is None


def test_eliminar_inexistente_devuelve_false(grupo_trabajo_repo):
    assert grupo_trabajo_repo.eliminar("000000000000000000000000") is False
