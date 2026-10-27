import pytest

from app.domain.rol import Rol
from app.domain.usuario import Usuario
from app.domain.reporte import Reporte

pytestmark = pytest.mark.integration


@pytest.fixture
def id_usuario_valido(rol_repo, usuario_repo):
    id_rol = rol_repo.crear(Rol(descripcion="TEST_RolReporte"))
    return usuario_repo.crear(
        Usuario(
            nombre="TEST_UsuarioReporte",
            apellido="Apellido",
            email="reporte1@example.com",
            id_rol=id_rol,
            password_hash="hash-de-prueba",
        )
    )


def test_crear_y_recuperar_por_id(reporte_repo, id_usuario_valido):
    id_reporte = reporte_repo.crear(
        Reporte(id_usuario=id_usuario_valido, tipo="TEST_envios_por_cliente", formato="pdf")
    )

    recuperado = reporte_repo.obtener_por_id(id_reporte)

    assert recuperado is not None
    assert recuperado.tipo == "TEST_envios_por_cliente"
    assert recuperado.formato == "pdf"


def test_listar_por_usuario(reporte_repo, id_usuario_valido):
    id_reporte = reporte_repo.crear(Reporte(id_usuario=id_usuario_valido, tipo="TEST_incidentes", formato="csv"))

    reportes = reporte_repo.listar_por_usuario(id_usuario_valido)

    assert any(r.id_reporte == id_reporte for r in reportes)


def test_eliminar_borra_la_fila(reporte_repo, id_usuario_valido):
    id_reporte = reporte_repo.crear(Reporte(id_usuario=id_usuario_valido, tipo="TEST_paraborrar", formato="xlsx"))

    reporte_repo.eliminar(id_reporte)

    assert reporte_repo.obtener_por_id(id_reporte) is None
