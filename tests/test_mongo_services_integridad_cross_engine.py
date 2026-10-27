"""Verifica que los Services de Mongo validan las referencias a MySQL en la
capa de aplicación (no hay FK nativas cross-engine — ver desafío de
complejidad adicional)."""
import pytest

from app.core.exceptions import ValidationError
from app.domain.evento_logistico import EventoLogistico
from app.domain.incidente import Incidente
from app.domain.mensaje import Mensaje
from app.domain.prediccion_riesgo import PrediccionRiesgo
from app.domain.rol import Rol
from app.domain.usuario import Usuario
from app.services.evento_logistico_service import EventoLogisticoService
from app.services.incidente_service import IncidenteService
from app.services.mensaje_service import MensajeService
from app.services.prediccion_riesgo_service import PrediccionRiesgoService

pytestmark = pytest.mark.integration

_ID_ENVIO_INEXISTENTE = 999999999


@pytest.fixture
def id_usuario_valido(rol_repo, usuario_repo):
    id_rol = rol_repo.crear(Rol(descripcion="TEST_RolMensajeCrossEngine"))
    return usuario_repo.crear(
        Usuario(
            nombre="TEST_UsuarioMensajeCrossEngine",
            apellido="Apellido",
            email="mensajecrossengine1@example.com",
            id_rol=id_rol,
            password_hash="hash-de-prueba",
        )
    )


def test_evento_logistico_rechaza_envio_inexistente(evento_logistico_repo):
    service = EventoLogisticoService(repository=evento_logistico_repo)

    with pytest.raises(ValidationError):
        service.registrar(EventoLogistico(id_envio=_ID_ENVIO_INEXISTENTE, tipo_evento="TEST_x"))


def test_incidente_rechaza_envio_inexistente(incidente_repo):
    service = IncidenteService(repository=incidente_repo)

    with pytest.raises(ValidationError):
        service.registrar(Incidente(id_envio=_ID_ENVIO_INEXISTENTE, tipo="TEST_x", severidad="baja"))


def test_prediccion_rechaza_envio_inexistente(prediccion_riesgo_repo):
    service = PrediccionRiesgoService(repository=prediccion_riesgo_repo)

    with pytest.raises(ValidationError):
        service.registrar(PrediccionRiesgo(id_envio=_ID_ENVIO_INEXISTENTE, probabilidad_demora=0.5))


def test_mensaje_privado_rechaza_destinatario_inexistente(mensaje_repo, id_usuario_valido):
    service = MensajeService(repository=mensaje_repo)

    with pytest.raises(ValidationError):
        service.enviar(
            Mensaje(
                id_remitente=id_usuario_valido,
                id_destinatario=_ID_ENVIO_INEXISTENTE,
                contenido="TEST_x",
                tipo="privado",
            )
        )
