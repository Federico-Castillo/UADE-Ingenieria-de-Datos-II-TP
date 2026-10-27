import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from mysql.connector import Error as MySQLError

from app.db.mysql import get_cursor, transaction
from app.repositories.cliente_repository import ClienteRepository
from app.repositories.operador_logistico_repository import OperadorLogisticoRepository
from app.repositories.proveedor_repository import ProveedorRepository
from app.repositories.rol_repository import RolRepository
from app.repositories.sesion_repository import SesionRepository
from app.repositories.usuario_repository import UsuarioRepository

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


@pytest.fixture
def rol_repo(mysql_connection) -> RolRepository:
    return RolRepository()


@pytest.fixture
def proveedor_repo(mysql_connection) -> ProveedorRepository:
    return ProveedorRepository()


@pytest.fixture
def operador_logistico_repo(mysql_connection) -> OperadorLogisticoRepository:
    return OperadorLogisticoRepository()


@pytest.fixture
def usuario_repo(mysql_connection) -> UsuarioRepository:
    return UsuarioRepository()


@pytest.fixture
def sesion_repo() -> SesionRepository:
    return SesionRepository()


@pytest.fixture
def sesiones_creadas(sesion_repo):
    """Lista mutable donde el test registra los id_sesion que crea, para
    cerrarlas (y limpiar Redis) automáticamente al final sin esperar el TTL."""
    creadas: list[str] = []
    yield creadas
    for id_sesion in creadas:
        sesion_repo.cerrar(id_sesion)


@pytest.fixture(autouse=True)
def limpiar_datos_de_test(mysql_connection):
    def _borrar():
        with transaction() as cursor:
            # Orden por dependencias de FK: usuario referencia rol y cliente.
            cursor.execute("DELETE FROM usuario WHERE nombre LIKE %s", (f"{TEST_PREFIX}%",))
            cursor.execute("DELETE FROM cliente WHERE razon_social LIKE %s", (f"{TEST_PREFIX}%",))
            cursor.execute("DELETE FROM rol WHERE descripcion LIKE %s", (f"{TEST_PREFIX}%",))
            cursor.execute("DELETE FROM proveedor WHERE razon_social LIKE %s", (f"{TEST_PREFIX}%",))
            cursor.execute(
                "DELETE FROM operador_logistico WHERE razon_social LIKE %s", (f"{TEST_PREFIX}%",)
            )

    _borrar()
    yield
    _borrar()
