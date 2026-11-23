"""Desplegables, confirmaciones, nombres legibles y grafos de la UI (sin DB ni NiceGUI)."""
import json
import sys
import types
from dataclasses import dataclass

import pytest

from app.ui import abm, grafos, opciones
from app.ui import reflexion as r


@pytest.fixture(autouse=True)
def limpiar_datos_de_test():
    yield


@pytest.fixture(autouse=True)
def limpiar_mongo_de_test():
    yield


@pytest.fixture(autouse=True)
def limpiar_neo4j_de_test():
    yield


# ---------- opciones (desplegables) ----------

def test_opciones_desde_constantes_del_modulo():
    mod = types.SimpleNamespace(_PRIORIDADES_VALIDAS={"baja", "alta"}, _OPERADORES_VALIDOS={">", "<"},
                                _MEDIOS_VALIDOS={"aereo"}, _OTRA_COSA={"x"})
    assert opciones.opciones_de("prioridad", modulo=mod) == ["alta", "baja"]
    assert opciones.opciones_de("operador_comparacion", modulo=mod) == ["<", ">"]  # prefijo "operador_"
    assert opciones.opciones_de("medio_transporte", modulo=mod) == ["aereo"]
    assert opciones.opciones_de("nombre", modulo=mod) is None


def test_opciones_desde_enum_del_esquema_mysql():
    @dataclass
    class Cliente:
        estado: str = "activo"

    assert opciones.opciones_de("estado", clase=Cliente) == ["activo", "inactivo"]
    assert opciones.opciones_de("razon_social", clase=Cliente) is None


def test_los_services_reales_exponen_desplegables():
    from app.services.envio_service import EnvioService
    from app.services.regla_service import ReglaService

    (envio,) = r.parametros_de(EnvioService.dar_alta)
    por_nombre = {c.nombre: c for c in envio.campos}
    assert por_nombre["prioridad"].opciones == ["alta", "baja", "normal", "urgente"]
    assert "en_transito" in por_nombre["estado"].opciones
    assert por_nombre["origen"].opciones is None
    (regla,) = r.parametros_de(ReglaService.dar_alta)
    campos = {c.nombre: c for c in regla.campos}
    assert campos["tipo_sensor"].opciones == ["temperatura", "humedad", "vibracion", "bateria"]
    assert campos["operador_comparacion"].opciones == [">", ">=", "<", "<=", "="]
    assert campos["severidad"].opciones == ["alta", "baja", "critica", "media"]


# ---------- confirmaciones, nombres y descripciones ----------

def test_riesgo_de_operaciones():
    assert abm.riesgo_de("dar_baja") == "baja"
    assert abm.riesgo_de("eliminar") == "baja"
    assert abm.riesgo_de("quitar_integrante") == "baja"
    assert abm.riesgo_de("cerrar_sesion") == "baja"
    assert abm.riesgo_de("ejecutar_cierre_mensual") == "proceso"
    assert abm.riesgo_de("listar") is None
    assert abm.riesgo_de("dar_alta") is None


def test_nombre_legible_y_descripcion():
    assert r.nombre_legible("listar_por_cliente") == "Listar por cliente"

    class _S:
        def con_doc(self):
            """Primera línea
            sigue acá.

            Segundo párrafo que no se muestra."""

        def sin_doc(self): ...

    assert r.descripcion_de(_S().con_doc) == "Primera línea sigue acá."
    assert r.descripcion_de(_S().sin_doc) == ""


# ---------- grafos ----------

def test_opciones_red_deduplica_y_serializa():
    filas = [
        {"id_cliente": 1, "cliente": "A", "id_operador_logistico": 9, "operador": "Op"},
        {"id_cliente": 1, "cliente": "A", "id_operador_logistico": 9, "operador": "Op"},  # repetida
        {"id_cliente": 2, "cliente": "B", "id_operador_logistico": 9, "operador": "Op"},
    ]
    serie = grafos.opciones_red(filas)["series"][0]
    assert len(serie["data"]) == 3 and len(serie["links"]) == 2
    op = next(n for n in serie["data"] if n["id"] == "o9")
    assert op["category"] == 1 and op["symbolSize"] > next(n for n in serie["data"] if n["id"] == "c2")["symbolSize"]
    json.dumps(grafos.opciones_red(filas))


def test_opciones_ruta_encadena_tramos_en_orden():
    tramos = [
        {"orden": 2, "origen": "Madrid", "destino": "Roma", "medio_transporte": "aereo", "vehiculo": "V2"},
        {"orden": 1, "origen": "Buenos Aires", "destino": "Madrid", "medio_transporte": "maritimo", "vehiculo": None},
    ]
    serie = grafos.opciones_ruta(tramos, 53)["series"][0]
    assert [n["name"] for n in serie["data"]] == ["Buenos Aires", "Madrid", "Roma"]
    assert [(l["source"], l["target"]) for l in serie["links"]] == [("n0", "n1"), ("n1", "n2")]
    assert "s/vehículo" in serie["links"][0]["value"]
    assert grafos.opciones_ruta([], 1)["series"][0]["data"] == []
