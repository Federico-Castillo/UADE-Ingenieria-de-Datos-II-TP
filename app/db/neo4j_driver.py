"""Driver y sesiones de Neo4j."""
import logging
from contextlib import contextmanager

from neo4j import GraphDatabase
from neo4j.exceptions import Neo4jError, ServiceUnavailable

from app.config import get_config

logger = logging.getLogger(__name__)

_driver = None


def get_driver():
    global _driver
    if _driver is None:
        config = get_config().neo4j
        try:
            _driver = GraphDatabase.driver(config.uri, auth=(config.user, config.password))
            _driver.verify_connectivity()
            logger.info("Conexión a Neo4j establecida (%s)", config.uri)
        except (Neo4jError, ServiceUnavailable):
            logger.exception("No se pudo conectar a Neo4j")
            raise
    return _driver


@contextmanager
def session():
    drv = get_driver()
    sess = drv.session()
    try:
        yield sess
    finally:
        sess.close()
