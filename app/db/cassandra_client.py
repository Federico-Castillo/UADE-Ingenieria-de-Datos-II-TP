"""Cluster y sesiones de Cassandra. Reusable por la app y por el futuro script
simulador de sensores IoT (de ahí que get_session() sea genérico, no atado a CLI)."""
import logging

from app.db import _cassandra_compat  # noqa: F401 - debe importarse antes que cassandra.cluster

from cassandra.cluster import Cluster
from cassandra.cluster import NoHostAvailable
from cassandra.io.asyncioreactor import AsyncioConnection

from app.config import get_config

logger = logging.getLogger(__name__)

_cluster: Cluster | None = None


def get_cluster() -> Cluster:
    global _cluster
    if _cluster is None:
        config = get_config().cassandra
        try:
            # Python 3.12 removió `asyncore` (default del driver) y no hay
            # extensión C de libev compilada en Windows; AsyncioConnection usa
            # asyncio nativo y funciona sin dependencias extra.
            _cluster = Cluster(
                contact_points=config.hosts,
                port=config.port,
                connection_class=AsyncioConnection,
            )
            logger.info("Cluster de Cassandra creado (%s:%s)", config.hosts, config.port)
        except NoHostAvailable:
            logger.exception("No se pudo crear el cluster de Cassandra")
            raise
    return _cluster


def get_session(keyspace: str | None = None):
    """keyspace=None se usa antes de que el keyspace exista (ej. el script de
    creación de esquema). Con keyspace seteado, sirve para la app y el simulador IoT."""
    cluster = get_cluster()
    try:
        session = cluster.connect(keyspace) if keyspace else cluster.connect()
        logger.info("Sesión de Cassandra abierta (keyspace=%s)", keyspace)
        return session
    except NoHostAvailable:
        logger.exception("No se pudo abrir sesión de Cassandra")
        raise
