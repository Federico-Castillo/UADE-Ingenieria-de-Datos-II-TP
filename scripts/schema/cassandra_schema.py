"""Ejecuta cassandra_schema.cql (keyspace + tabla) vía cassandra-driver."""
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.db.cassandra_client import get_session  # noqa: E402 - aplica el shim de compat antes de cassandra.cluster

from cassandra.cluster import NoHostAvailable

logger = logging.getLogger(__name__)

CQL_FILE = os.path.join(os.path.dirname(__file__), "cassandra_schema.cql")


def create_schema() -> None:
    with open(CQL_FILE, encoding="utf-8") as f:
        statements = [s.strip() for s in f.read().split(";") if s.strip()]

    sess = get_session(keyspace=None)
    for statement in statements:
        sess.execute(statement)
        logger.info("Ejecutado: %s", statement)

    logger.info("Esquema de Cassandra listo (%s statements)", len(statements))


if __name__ == "__main__":
    from app.logging_config import setup_logging

    setup_logging()
    try:
        create_schema()
        print("Cassandra: OK")
    except NoHostAvailable as e:
        print(f"Cassandra: ERROR ({e})")
        raise
