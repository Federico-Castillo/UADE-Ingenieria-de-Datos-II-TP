from app.core.exceptions import ValidationError
from app.domain.mensaje import Mensaje
from app.repositories.grupo_trabajo_repository import GrupoTrabajoRepository
from app.repositories.mensaje_repository import MensajeRepository
from app.repositories.usuario_repository import UsuarioRepository

_TIPOS_VALIDOS = {"privado", "grupal"}


class MensajeService:
    def __init__(
        self,
        repository: MensajeRepository | None = None,
        usuario_repository: UsuarioRepository | None = None,
        grupo_repository: GrupoTrabajoRepository | None = None,
    ):
        self._repo = repository or MensajeRepository()
        self._usuario_repo = usuario_repository or UsuarioRepository()
        self._grupo_repo = grupo_repository or GrupoTrabajoRepository()

    def enviar(self, mensaje: Mensaje) -> Mensaje:
        if not mensaje.contenido or not mensaje.contenido.strip():
            raise ValidationError("El contenido no puede estar vacío.")
        if mensaje.tipo not in _TIPOS_VALIDOS:
            raise ValidationError(f"Tipo inválido. Opciones: {', '.join(sorted(_TIPOS_VALIDOS))}.")
        if self._usuario_repo.obtener_por_id(mensaje.id_remitente) is None:
            raise ValidationError(f"No existe el usuario remitente con id {mensaje.id_remitente}.")

        if mensaje.tipo == "privado":
            if mensaje.id_destinatario is None:
                raise ValidationError("Un mensaje privado necesita un destinatario.")
            if self._usuario_repo.obtener_por_id(mensaje.id_destinatario) is None:
                raise ValidationError(f"No existe el usuario destinatario con id {mensaje.id_destinatario}.")
        else:
            if mensaje.id_grupo is None:
                raise ValidationError("Un mensaje grupal necesita un grupo.")
            if self._grupo_repo.obtener_por_id(mensaje.id_grupo) is None:
                raise ValidationError(f"No existe el grupo con id {mensaje.id_grupo}.")

        id_mensaje = self._repo.crear(mensaje)
        mensaje.id_mensaje = id_mensaje
        return mensaje

    def listar_conversacion_privada(self, id_usuario_a: int, id_usuario_b: int) -> list[Mensaje]:
        if self._usuario_repo.obtener_por_id(id_usuario_a) is None:
            raise ValidationError(f"No existe el usuario con id {id_usuario_a}.")
        if self._usuario_repo.obtener_por_id(id_usuario_b) is None:
            raise ValidationError(f"No existe el usuario con id {id_usuario_b}.")
        return self._repo.listar_conversacion_privada(id_usuario_a, id_usuario_b)

    def listar_de_grupo(self, id_grupo: str) -> list[Mensaje]:
        if self._grupo_repo.obtener_por_id(id_grupo) is None:
            raise ValidationError(f"No existe el grupo con id {id_grupo}.")
        return self._repo.listar_de_grupo(id_grupo)
