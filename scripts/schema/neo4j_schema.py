"""Ejecuta neo4j_schema.cypher (constraints/índices) vía el driver de Neo4j."""
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from neo4j.exceptions import Neo4jError

from app.db.neo4j_driver import session

logger = logging.getLogger(__name__)

CYPHER_FILE = os.path.join(os.path.dirname(__file__), "neo4j_schema.cypher")


def create_schema() -> None:
    with open(CYPHER_FILE, encoding="utf-8") as f:
        statements = [s.strip() for s in f.read().split(";") if s.strip()]

    with session() as sess:
        for statement in statements:
            sess.run(statement)
            logger.info("Ejecutado: %s", statement)

    logger.info("Esquema de Neo4j listo (%s statements)", len(statements))


if __name__ == "__main__":
    from app.logging_config import setup_logging

    setup_logging()
    try:
        create_schema()
        print("Neo4j: OK")
    except Neo4jError as e:
        print(f"Neo4j: ERROR ({e})")
        raise
