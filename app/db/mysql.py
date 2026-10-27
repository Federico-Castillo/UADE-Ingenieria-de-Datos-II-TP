"""Conexión y manejo de transacciones para MySQL."""
import logging
from contextlib import contextmanager

import mysql.connector
from mysql.connector import Error as MySQLError

from app.config import get_config

logger = logging.getLogger(__name__)


def _connect():
    config = get_config().mysql
    try:
        conn = mysql.connector.connect(
            host=config.host,
            port=config.port,
            user=config.user,
            password=config.password,
            database=config.database,
        )
        logger.info(
            "Conexión a MySQL establecida (%s:%s/%s)",
            config.host, config.port, config.database,
        )
        return conn
    except MySQLError:
        logger.exception("No se pudo conectar a MySQL")
        raise


@contextmanager
def transaction():
    """Yields un cursor (dict rows). Commit automático si no hay excepción,
    rollback si la hay. Usar para operaciones de escritura."""
    conn = _connect()
    cursor = conn.cursor(dictionary=True)
    try:
        yield cursor
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


@contextmanager
def get_cursor():
    """Yields un cursor (dict rows) de solo lectura, sin necesidad de commit."""
    conn = _connect()
    cursor = conn.cursor(dictionary=True)
    try:
        yield cursor
    finally:
        cursor.close()
        conn.close()
