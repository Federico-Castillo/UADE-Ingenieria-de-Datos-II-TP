"""Acceso a datos de Sesión contra Redis. Modelo según modelado.md:
session:{id_sesion}        -> HASH { id_usuario, fecha_inicio, fecha_fin, estado } (TTL)
user_sessions:{id_usuario}  -> SET de id_sesion activos (sin TTL, se limpia por app)

A diferencia de las entidades en MySQL, id_sesion no es AUTO_INCREMENT: se
genera un UUID porque Redis no tiene secuencias nativas."""
import logging
import uuid
from datetime import datetime, timezone

from redis.exceptions import RedisError

from app.core.exceptions import RepositoryError
from app.db.redis_client import get_client
from app.domain.sesion import Sesion

logger = logging.getLogger(__name__)

TTL_SECONDS = 3600


def _session_key(id_sesion: str) -> str:
    return f"session:{id_sesion}"


def _user_sessions_key(id_usuario: int) -> str:
    return f"user_sessions:{id_usuario}"


def _hash_to_sesion(id_sesion: str, data: dict) -> Sesion:
    return Sesion(
        id_sesion=id_sesion,
        id_usuario=int(data["id_usuario"]),
        fecha_inicio=data["fecha_inicio"],
        fecha_fin=data.get("fecha_fin") or None,
        estado=data["estado"],
    )


class SesionRepository:
    def __init__(self):
        self._client = get_client()

    def crear(self, id_usuario: int) -> Sesion:
        try:
            id_sesion = uuid.uuid4().hex
            fecha_inicio = datetime.now(timezone.utc).isoformat()
            key = _session_key(id_sesion)
            self._client.hset(
                key,
                mapping={
                    "id_usuario": id_usuario,
                    "fecha_inicio": fecha_inicio,
                    "fecha_fin": "",
                    "estado": "activa",
                },
            )
            self._client.expire(key, TTL_SECONDS)
            self._client.sadd(_user_sessions_key(id_usuario), id_sesion)
            return Sesion(id_sesion=id_sesion, id_usuario=id_usuario, fecha_inicio=fecha_inicio)
        except RedisError as e:
            logger.exception("Error creando sesión")
            raise RepositoryError(f"No se pudo crear la sesión: {e}") from e

    def obtener(self, id_sesion: str) -> Sesion | None:
        try:
            data = self._client.hgetall(_session_key(id_sesion))
            return _hash_to_sesion(id_sesion, data) if data else None
        except RedisError as e:
            logger.exception("Error obteniendo sesión")
            raise RepositoryError(f"No se pudo obtener la sesión: {e}") from e

    def listar_activas_de_usuario(self, id_usuario: int) -> list[Sesion]:
        try:
            ids = self._client.smembers(_user_sessions_key(id_usuario))
            sesiones = []
            for id_sesion in ids:
                sesion = self.obtener(id_sesion)
                if sesion is not None:
                    sesiones.append(sesion)
                else:
                    # La key expiró por TTL pero quedó huérfana en el SET -> se limpia.
                    self._client.srem(_user_sessions_key(id_usuario), id_sesion)
            return sesiones
        except RedisError as e:
            logger.exception("Error listando sesiones del usuario")
            raise RepositoryError(f"No se pudo listar las sesiones del usuario: {e}") from e

    def listar_todas_activas(self) -> list[Sesion]:
        try:
            sesiones = []
            for key in self._client.scan_iter("session:*"):
                id_sesion = key.split(":", 1)[1]
                sesion = self.obtener(id_sesion)
                if sesion is not None:
                    sesiones.append(sesion)
            return sesiones
        except RedisError as e:
            logger.exception("Error listando todas las sesiones activas")
            raise RepositoryError(f"No se pudo listar las sesiones activas: {e}") from e

    def cerrar(self, id_sesion: str) -> bool:
        """Devuelve False si la sesión no existe (ya expiró o id inválido)."""
        try:
            data = self._client.hgetall(_session_key(id_sesion))
            if not data:
                return False
            self._client.delete(_session_key(id_sesion))
            self._client.srem(_user_sessions_key(int(data["id_usuario"])), id_sesion)
            return True
        except RedisError as e:
            logger.exception("Error cerrando sesión")
            raise RepositoryError(f"No se pudo cerrar la sesión: {e}") from e
