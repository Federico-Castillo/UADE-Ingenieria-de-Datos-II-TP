"""Orquesta la creación de esquema en los 5 motores. Un fallo en uno no aborta
los demás; imprime un resumen final OK/ERROR por motor."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.logging_config import setup_logging

setup_logging()

import logging

logger = logging.getLogger(__name__)

resultados: dict[str, str] = {}


def _run(nombre: str, fn) -> None:
    try:
        fn()
        resultados[nombre] = "OK"
    except Exception as e:  # noqa: BLE001 - queremos capturar cualquier fallo de driver
        logger.exception("Fallo creando esquema de %s", nombre)
        resultados[nombre] = f"ERROR ({e})"


def main() -> None:
    from scripts.schema import mysql_schema, mongo_schema, neo4j_schema, cassandra_schema
    from app.db.redis_client import get_client as get_redis_client

    _run("MySQL", mysql_schema.create_schema)
    _run("MongoDB", mongo_schema.create_schema)
    _run("Neo4j", neo4j_schema.create_schema)

    def _check_redis():
        get_redis_client().ping()

    _run("Redis (solo verifica conexión, no tiene esquema)", _check_redis)
    _run("Cassandra", cassandra_schema.create_schema)

    print("\n=== Resumen creación de esquema ===")
    for nombre, estado in resultados.items():
        print(f"{nombre}: {estado}")


if __name__ == "__main__":
    main()
