import pytest

from app.domain.rol import Rol

pytestmark = pytest.mark.integration


def _rol(descripcion: str, **kwargs) -> Rol:
    return Rol(descripcion=f"TEST_{descripcion}", **kwargs)


def test_crear_y_recuperar_por_id(rol_repo):
    id_rol = rol_repo.crear(_rol("Admin", nivel_permisos=10))

    recuperado = rol_repo.obtener_por_id(id_rol)

    assert recuperado is not None
    assert recuperado.descripcion == "TEST_Admin"
    assert recuperado.nivel_permisos == 10


def test_listar_incluye_el_creado(rol_repo):
    id_rol = rol_repo.crear(_rol("Operador"))

    roles = rol_repo.listar()

    assert any(r.id_rol == id_rol for r in roles)


def test_actualizar_modifica_los_campos(rol_repo):
    id_rol = rol_repo.crear(_rol("Original", nivel_permisos=1))
    rol = rol_repo.obtener_por_id(id_rol)

    rol.descripcion = "TEST_Modificado"
    rol.nivel_permisos = 5
    rol_repo.actualizar(rol)

    recuperado = rol_repo.obtener_por_id(id_rol)
    assert recuperado.descripcion == "TEST_Modificado"
    assert recuperado.nivel_permisos == 5


def test_eliminar_borra_la_fila(rol_repo):
    id_rol = rol_repo.crear(_rol("ParaBorrar"))

    rol_repo.eliminar(id_rol)

    assert rol_repo.obtener_por_id(id_rol) is None
