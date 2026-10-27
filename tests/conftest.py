import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from mysql.connector import Error as MySQLError

from app.db.mysql import get_cursor
from app.repositories.cliente_repository import ClienteRepository

TEST_PREFIX = "TEST_"


@pytest.fixture(scope="session")
def mysql_connection():
    try:
        with get_cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except MySQLError as e:
        pytest.fail(
            "No se pudo conectar a MySQL. ¿Corriste `docker-compose up -d` y "
            f"`python scripts/schema/mysql_schema.py`? Detalle: {e}"
        )
    yield


@pytest.fixture
def cliente_repo(mysql_connection) -> ClienteRepository:
    return ClienteRepository()


@pytest.fixture(autouse=True)
def limpiar_clientes(mysql_connection):
    def _borrar():
        with get_cursor() as cursor:
            cursor.execute(
                "SELECT id_cliente FROM cliente WHERE razon_social LIKE %s",
                (f"{TEST_PREFIX}%",),
            )
            ids = [row["id_cliente"] for row in cursor.fetchall()]
        if ids:
            from app.db.mysql import transaction

            with transaction() as cursor:
                cursor.execute(
                    "DELETE FROM cliente WHERE razon_social LIKE %s",
                    (f"{TEST_PREFIX}%",),
                )

    _borrar()
    yield
    _borrar()
