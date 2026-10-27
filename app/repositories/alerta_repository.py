"""Acceso a datos de Alerta contra Redis. Modelo según modelado.md:
alert:{id_alerta} -> HASH { id_sensor, id_evento, id_regla, tipo, fecha, estado } (TTL)
alerts:active      -> SET de id_alerta actualmente activos (índice manual, evita SCAN)."""
import logging
import uuid
from datetime import datetime, timezone

from redis.exceptions import RedisError

from app.core.exceptions import RepositoryError
from app.db.redis_client import get_client
from app.domain.alerta import Alerta

logger = logging.getLogger(__name__)

TTL_SECONDS = 86400  # 24hs
_ACTIVE_SET_KEY = "alerts:active"


def _alert_key(id_alerta: str) -> str:
    return f"alert:{id_alerta}"


def _hash_to_alerta(id_alerta: str, data: dict) -> Alerta:
    return Alerta(
        id_alerta=id_alerta,
        id_sensor=int(data["id_sensor"]),
        id_regla=int(data["id_regla"]),
        tipo=data["tipo"],
        fecha=data["fecha"],
        estado=data["estado"],
        id_evento=data.get("id_evento") or None,
    )


class AlertaRepository:
    def __init__(self):
        self._client = get_client()

    def crear(self, id_sensor: int, id_regla: int, tipo: str, id_evento: str | None = None) -> Alerta:
        try:
            id_alerta = uuid.uuid4().hex
            fecha = datetime.now(timezone.utc).isoformat()
            key = _alert_key(id_alerta)
            self._client.hset(
                key,
                mapping={
                    "id_sensor": id_sensor,
                    "id_evento": id_evento or "",
                    "id_regla": id_regla,
                    "tipo": tipo,
                    "fecha": fecha,
                    "estado": "activa",
                },
            )
            self._client.expire(key, TTL_SECONDS)
            self._client.sadd(_ACTIVE_SET_KEY, id_alerta)
            return Alerta(
                id_alerta=id_alerta, id_sensor=id_sensor, id_regla=id_regla,
                tipo=tipo, fecha=fecha, id_evento=id_evento,
            )
        except RedisError as e:
            logger.exception("Error creando alerta")
            raise RepositoryError(f"No se pudo crear la alerta: {e}") from e

    def obtener(self, id_alerta: str) -> Alerta | None:
        try:
            data = self._client.hgetall(_alert_key(id_alerta))
            return _hash_to_alerta(id_alerta, data) if data else None
        except RedisError as e:
            logger.exception("Error obteniendo alerta")
            raise RepositoryError(f"No se pudo obtener la alerta: {e}") from e

    def listar_activas(self) -> list[Alerta]:
        try:
            ids = self._client.smembers(_ACTIVE_SET_KEY)
            alertas = []
            for id_alerta in ids:
                alerta = self.obtener(id_alerta)
                if alerta is not None:
                    alertas.append(alerta)
                else:
                    # La key expiró por TTL pero quedó huérfana en el SET -> se limpia.
                    self._client.srem(_ACTIVE_SET_KEY, id_alerta)
            return alertas
        except RedisError as e:
            logger.exception("Error listando alertas activas")
            raise RepositoryError(f"No se pudo listar las alertas activas: {e}") from e

    def resolver(self, id_alerta: str) -> bool:
        """Devuelve False si la alerta no existe (ya expiró o id inválido)."""
        try:
            key = _alert_key(id_alerta)
            if not self._client.exists(key):
                return False
            self._client.delete(key)
            self._client.srem(_ACTIVE_SET_KEY, id_alerta)
            return True
        except RedisError as e:
            logger.exception("Error resolviendo alerta")
            raise RepositoryError(f"No se pudo resolver la alerta: {e}") from e
