"""Ejecuta mysql_schema.sql (17 tablas + índices) contra MySQL."""
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import mysql.connector
from mysql.connector import Error as MySQLError

from app.config import get_config

logger = logging.getLogger(__name__)

SQL_FILE = os.path.join(os.path.dirname(__file__), "mysql_schema.sql")


def create_schema() -> None:
    with open(SQL_FILE, encoding="utf-8") as f:
        statements = [s.strip() for s in f.read().split(";") if s.strip()]

    config = get_config().mysql
    conn = mysql.connector.connect(
        host=config.host, port=config.port, user=config.user, password=config.password
    )
    conn.autocommit = True
    cursor = conn.cursor()
    try:
        for statement in statements:
            cursor.execute(statement)
            logger.info("Ejecutado: %s", statement.splitlines()[0])
    finally:
        cursor.close()
        conn.close()

    logger.info("Esquema de MySQL listo (%s statements)", len(statements))


if __name__ == "__main__":
    from app.logging_config import setup_logging

    setup_logging()
    try:
        create_schema()
        print("MySQL: OK")
    except MySQLError as e:
        print(f"MySQL: ERROR ({e})")
        raise
