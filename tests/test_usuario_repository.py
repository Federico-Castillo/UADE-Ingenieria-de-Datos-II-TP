import pytest

from app.core.exceptions import DuplicateError
from app.domain.usuario import Usuario

pytestmark = pytest.mark.integration


@pytest.fixture
def id_rol_valido(rol_repo):
    from app.domain.rol import Rol

    return rol_repo.crear(Rol(descripcion="TEST_RolUsuario", nivel_permisos=1))


def _usuario(nombre: str, email: str, id_rol: int, **kwargs) -> Usuario:
    return Usuario(
        nombre=f"TEST_{nombre}",
        apellido="Apellido",
        email=email,
        id_rol=id_rol,
        password_hash="hash-de-prueba",
        **kwargs,
    )


def test_crear_y_recuperar_por_id(usuario_repo, id_rol_valido):
    id_usuario = usuario_repo.crear(_usuario("Juan", "user1@example.com", id_rol_valido))

    recuperado = usuario_repo.obtener_por_id(id_usuario)

    assert recuperado is not None
    assert recuperado.nombre == "TEST_Juan"
    assert recuperado.id_rol == id_rol_valido
    assert recuperado.estado == "activo"


def test_email_duplicado_lanza_duplicate_error(usuario_repo, id_rol_valido):
    usuario_repo.crear(_usuario("A", "user2@example.com", id_rol_valido))

    with pytest.raises(DuplicateError):
        usuario_repo.crear(_usuario("B", "user2@example.com", id_rol_valido))


def test_baja_logica_no_borra_la_fila(usuario_repo, id_rol_valido):
    id_usuario = usuario_repo.crear(_usuario("ParaBaja", "user3@example.com", id_rol_valido))

    usuario_repo.eliminar(id_usuario)

    recuperado = usuario_repo.obtener_por_id(id_usuario)
    assert recuperado is not None
    assert recuperado.estado == "inactivo"


def test_buscar_matchea_texto_parcial(usuario_repo, id_rol_valido):
    usuario_repo.crear(_usuario("Carlos Buscable", "user4@example.com", id_rol_valido))

    resultados = usuario_repo.buscar("Buscable")

    assert any(u.nombre == "TEST_Carlos Buscable" for u in resultados)
