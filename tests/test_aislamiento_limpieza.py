"""La limpieza de conftest.py no deja residuos de outbox de entidades que el propio test
dio de baja (punto 6 de los pendientes: la suite ensuciaba la base de desarrollo)."""
import pytest

from app.db.mysql import get_cursor
from app.domain.cliente import Cliente
from app.domain.envio import Envio
from tests.conftest import _MARGEN, _borrar_outbox_huerfano

pytestmark = pytest.mark.integration


def _eventos(entidad: str, id_entidad: int) -> int:
    with get_cursor() as cursor:
        cursor.execute(
            "SELECT COUNT(*) AS n FROM outbox_eventos WHERE entidad = %s AND id_entidad = %s", (entidad, id_entidad)
        )
        return cursor.fetchone()["n"]


def test_borra_el_outbox_de_un_envio_dado_de_baja_y_conserva_el_de_uno_vivo(cliente_repo, envio_repo):
    with get_cursor() as cursor:
        cursor.execute("SELECT NOW() AS ahora")
        desde = cursor.fetchone()["ahora"] - _MARGEN

    id_cliente = cliente_repo.crear(
        Cliente(razon_social="TEST_LimpiezaOutbox", cuit="90-99000123-4", email="limpieza@example.com")
    )
    id_vivo = envio_repo.crear(Envio(id_cliente=id_cliente, origen="TEST_Vivo", destino="Destino"))
    id_baja = envio_repo.crear(Envio(id_cliente=id_cliente, origen="TEST_Baja", destino="Destino"))
    envio_repo.eliminar(id_baja)
    assert _eventos("envio", id_baja) == 2  # 'creado' + 'eliminado', y el envío ya no existe

    _borrar_outbox_huerfano(desde)

    assert _eventos("envio", id_baja) == 0
    assert _eventos("envio", id_vivo) == 1   # entidad viva: no se toca
    assert _eventos("cliente", id_cliente) >= 1
