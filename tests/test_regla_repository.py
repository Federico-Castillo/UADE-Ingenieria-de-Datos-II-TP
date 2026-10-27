import pytest

from app.domain.rol import Rol
from app.domain.usuario import Usuario
from app.domain.regla import Regla

pytestmark = pytest.mark.integration


@pytest.fixture
def id_usuario_valido(rol_repo, usuario_repo):
    id_rol = rol_repo.crear(Rol(descripcion="TEST_RolRegla"))
    return usuario_repo.crear(
        Usuario(
            nombre="TEST_UsuarioRegla",
            apellido="Apellido",
            email="regla1@example.com",
            id_rol=id_rol,
            password_hash="hash-de-prueba",
        )
    )


def _regla(nombre: str, id_usuario_creador: int, **kwargs) -> Regla:
    defaults = dict(
        tipo_sensor="temperatura",
        operador_comparacion=">",
        valor_umbral=40.0,
        severidad="alta",
    )
    defaults.update(kwargs)
    return Regla(nombre=nombre, id_usuario_creador=id_usuario_creador, **defaults)


def test_crear_y_recuperar_por_id(regla_repo, id_usuario_valido):
    id_regla = regla_repo.crear(_regla("TEST_ReglaTemp", id_usuario_valido))

    recuperada = regla_repo.obtener_por_id(id_regla)

    assert recuperada is not None
    assert recuperada.nombre == "TEST_ReglaTemp"
    assert recuperada.estado == "activa"


def test_listar_solo_activas(regla_repo, id_usuario_valido):
    id_activa = regla_repo.crear(_regla("TEST_Activa", id_usuario_valido))
    id_inactiva = regla_repo.crear(_regla("TEST_Inactiva", id_usuario_valido))
    inactiva = regla_repo.obtener_por_id(id_inactiva)
    inactiva.estado = "inactiva"
    regla_repo.actualizar(inactiva)

    activas = regla_repo.listar(solo_activas=True)
    ids_activas = {r.id_regla for r in activas}

    assert id_activa in ids_activas
    assert id_inactiva not in ids_activas


def test_eliminar_borra_la_fila(regla_repo, id_usuario_valido):
    id_regla = regla_repo.crear(_regla("TEST_ParaBorrar", id_usuario_valido))

    regla_repo.eliminar(id_regla)

    assert regla_repo.obtener_por_id(id_regla) is None
