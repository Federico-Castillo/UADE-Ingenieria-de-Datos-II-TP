"""Cliente Redis (singleton perezoso)."""
import logging

import redis
from redis.exceptions import RedisError

from app.config import get_config

logger = logging.getLogger(__name__)

_client: redis.Redis | None = None


def get_client() -> redis.Redis:
    global _client
    if _client is None:
        config = get_config().redis
        try:
            _client = redis.Redis(
                host=config.host, port=config.port, db=config.db, decode_responses=True
            )
            _client.ping()
            logger.info("Conexión a Redis establecida (%s:%s/%s)", config.host, config.port, config.db)
        except RedisError:
            logger.exception("No se pudo conectar a Redis")
            raise
    return _client
