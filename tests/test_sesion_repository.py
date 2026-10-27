import pytest

pytestmark = pytest.mark.integration

_ID_USUARIO_TEST = 900001


def test_crear_y_obtener(sesion_repo, sesiones_creadas):
    sesion = sesion_repo.crear(_ID_USUARIO_TEST)
    sesiones_creadas.append(sesion.id_sesion)

    recuperada = sesion_repo.obtener(sesion.id_sesion)

    assert recuperada is not None
    assert recuperada.id_usuario == _ID_USUARIO_TEST
    assert recuperada.estado == "activa"


def test_listar_activas_de_usuario(sesion_repo, sesiones_creadas):
    sesion = sesion_repo.crear(_ID_USUARIO_TEST)
    sesiones_creadas.append(sesion.id_sesion)

    activas = sesion_repo.listar_activas_de_usuario(_ID_USUARIO_TEST)

    assert any(s.id_sesion == sesion.id_sesion for s in activas)


def test_listar_todas_activas_incluye_la_creada(sesion_repo, sesiones_creadas):
    sesion = sesion_repo.crear(_ID_USUARIO_TEST)
    sesiones_creadas.append(sesion.id_sesion)

    todas = sesion_repo.listar_todas_activas()

    assert any(s.id_sesion == sesion.id_sesion for s in todas)


def test_cerrar_elimina_la_sesion(sesion_repo):
    sesion = sesion_repo.crear(_ID_USUARIO_TEST)

    cerrada = sesion_repo.cerrar(sesion.id_sesion)

    assert cerrada is True
    assert sesion_repo.obtener(sesion.id_sesion) is None
    assert sesion.id_sesion not in [
        s.id_sesion for s in sesion_repo.listar_activas_de_usuario(_ID_USUARIO_TEST)
    ]


def test_cerrar_sesion_inexistente_devuelve_false(sesion_repo):
    assert sesion_repo.cerrar("id-que-no-existe") is False
