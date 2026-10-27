import pytest

from app.domain.grupo_trabajo import GrupoTrabajo
from app.domain.mensaje import Mensaje

pytestmark = pytest.mark.integration


@pytest.fixture
def id_grupo_valido(grupo_trabajo_repo):
    return grupo_trabajo_repo.crear(GrupoTrabajo(nombre="TEST_GrupoMensajes", integrantes=[10, 20]))


def test_listar_conversacion_privada(mensaje_repo):
    mensaje_repo.crear(Mensaje(id_remitente=10, id_destinatario=20, contenido="TEST_hola", tipo="privado"))
    mensaje_repo.crear(Mensaje(id_remitente=20, id_destinatario=10, contenido="TEST_respuesta", tipo="privado"))

    conversacion = mensaje_repo.listar_conversacion_privada(10, 20)
    contenidos = [m.contenido for m in conversacion]

    assert "TEST_hola" in contenidos
    assert "TEST_respuesta" in contenidos


def test_listar_de_grupo(mensaje_repo, id_grupo_valido):
    mensaje_repo.crear(
        Mensaje(id_remitente=10, id_grupo=id_grupo_valido, contenido="TEST_mensaje_grupal", tipo="grupal")
    )

    mensajes = mensaje_repo.listar_de_grupo(id_grupo_valido)

    assert any(m.contenido == "TEST_mensaje_grupal" for m in mensajes)
