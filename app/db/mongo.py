"""Cliente MongoDB (singleton perezoso)."""
import logging

from pymongo import MongoClient
from pymongo.errors import PyMongoError

from app.config import get_config

logger = logging.getLogger(__name__)

_client: MongoClient | None = None


def get_client() -> MongoClient:
    global _client
    if _client is None:
        config = get_config().mongo
        try:
            _client = MongoClient(host=config.host, port=config.port)
            _client.admin.command("ping")
            logger.info("Conexión a MongoDB establecida (%s:%s)", config.host, config.port)
        except PyMongoError:
            logger.exception("No se pudo conectar a MongoDB")
            raise
    return _client


def get_db():
    return get_client()[get_config().mongo.database]
