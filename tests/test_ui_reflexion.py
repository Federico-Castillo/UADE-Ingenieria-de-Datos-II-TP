"""Tests de la introspección de services usada por la UI (sin DB ni NiceGUI)."""
from datetime import datetime
from decimal import Decimal

import pytest

from app.domain.cliente import Cliente
from app.ui import reflexion as r


# Puro: sin DB. Anula las fixtures autouse de limpieza de conftest.py, que
# exigen MySQL/Mongo/Neo4j levantados.
@pytest.fixture(autouse=True)
def limpiar_datos_de_test():
    yield


@pytest.fixture(autouse=True)
def limpiar_mongo_de_test():
    yield


@pytest.fixture(autouse=True)
def limpiar_neo4j_de_test():
    yield


class _Falso:
    def alta(self, cliente: Cliente) -> Cliente: ...
    def por_id(self, id_cliente: int) -> Cliente: ...
    def listar(self, solo_activos: bool = False) -> list: ...
    def rango(self, id_sensor: int, desde: datetime, hasta: datetime) -> list: ...
    def ultima(self, limite: int | None = None): ...
    def _privado(self): ...


def test_metodos_publicos_excluye_privados():
    assert r.metodos_publicos(_Falso()) == ["alta", "listar", "por_id", "rango", "ultima"]


def test_parametro_dataclass_se_expande_en_campos():
    (p,) = r.parametros_de(_Falso().alta)
    assert p.es_objeto and p.clase is Cliente
    por_nombre = {c.nombre: c for c in p.campos}
    assert por_nombre["razon_social"].requerido
    assert not por_nombre["telefono"].requerido
    assert por_nombre["estado"].default == "activo"


def test_parametros_simples_y_defaults():
    (p,) = r.parametros_de(_Falso().listar)
    assert p.campo.tipo == "bool" and not p.campo.requerido
    (q,) = r.parametros_de(_Falso().ultima)
    assert q.campo.tipo == "int" and not q.campo.requerido


def test_construir_argumentos_con_dataclass():
    params = r.parametros_de(_Falso().alta)
    kwargs = r.construir_argumentos(params, {"cliente": {
        "razon_social": "ACME", "cuit": "20-12345678-9", "email": "a@b.com",
        "telefono": "", "direccion": "", "pais": "AR", "estado": "activo", "id_cliente": "",
    }})
    c = kwargs["cliente"]
    assert isinstance(c, Cliente) and c.telefono is None and c.id_cliente is None and c.pais == "AR"


def test_construir_argumentos_datetime_e_int():
    params = r.parametros_de(_Falso().rango)
    kwargs = r.construir_argumentos(params, {"id_sensor": "3", "desde": "2026-01-01 10:00", "hasta": "2026-01-02"})
    assert kwargs["id_sensor"] == 3 and kwargs["desde"] == datetime(2026, 1, 1, 10, 0)


def test_requerido_vacio_y_valor_invalido_dan_value_error():
    params = r.parametros_de(_Falso().por_id)
    with pytest.raises(ValueError, match="obligatorio"):
        r.construir_argumentos(params, {"id_cliente": ""})
    with pytest.raises(ValueError, match="inválido"):
        r.construir_argumentos(params, {"id_cliente": "abc"})


def test_convertir_decimal_con_coma():
    c = r.Campo("importe", "decimal", requerido=True)
    assert r.convertir("10,50", c) == Decimal("10.50")


def test_a_filas():
    c = Cliente("A", "20-1-1", "a@b.com")
    assert r.a_filas([c])[0]["razon_social"] == "A"
    assert r.a_filas([{"pais": "AR", "cantidad": 2}]) == [{"pais": "AR", "cantidad": 2}]
    assert r.a_filas(None) is None
    assert r.a_filas([1, 2]) == [{"valor": 1}, {"valor": 2}]
