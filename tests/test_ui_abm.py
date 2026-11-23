"""Detección de capacidades ABM y precarga de formularios (sin DB ni NiceGUI)."""
from dataclasses import dataclass
from datetime import date, datetime

import pytest

from app.ui import abm
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


@dataclass
class _Ent:
    nombre: str
    id_dueno: int
    notas: list[int] | None = None
    estado: str = "activo"
    id_ent: int | None = None


class _ServicioCompleto:
    def dar_alta(self, e: _Ent) -> _Ent: ...
    def modificar(self, e: _Ent) -> None: ...
    def dar_baja(self, id_ent: int) -> None: ...
    def listar(self, solo_activos: bool = False) -> list: ...
    def buscar(self, texto: str) -> list: ...


class _ServicioSoloAlta:
    def registrar(self, e: _Ent) -> _Ent: ...
    def listar_por_dueno(self, id_dueno: int) -> list: ...


class _ServicioListarObligatorio:
    def listar(self, id_dueno: int) -> list: ...


def test_detecta_abm_completo_sobre_la_clase():
    c = abm.detectar(_ServicioCompleto)  # clase, sin instanciar
    assert (c.listar, c.alta, c.modificar, c.baja, c.buscar) == ("listar", "dar_alta", "modificar", "dar_baja", "buscar")
    assert c.es_abm


def test_sin_listar_no_es_abm_y_listar_con_obligatorios_tampoco():
    assert not abm.detectar(_ServicioSoloAlta).es_abm
    assert abm.detectar(_ServicioSoloAlta).alta == "registrar"
    assert not abm.detectar(_ServicioListarObligatorio).es_abm


def test_clave_primaria_es_el_ultimo_id_opcional():
    assert abm.clave_primaria(_Ent) == "id_ent"
    assert abm.nombre_param_baja(_ServicioCompleto, abm.detectar(_ServicioCompleto)) == "id_ent"


def test_roundtrip_edicion_objeto_a_formulario_a_objeto():
    original = _Ent("ACME", 7, notas=[1, 2], estado="inactivo", id_ent=5)
    params = r.parametros_de(_ServicioCompleto.modificar)
    textos = {c.nombre: abm.texto_inicial(getattr(original, c.nombre)) for c in params[0].campos}
    assert textos["notas"] == "1,2" and textos["id_ent"] == "5"
    reconstruido = r.construir_argumentos(params, {"e": textos})["e"]
    assert reconstruido == original


def test_texto_inicial_fechas_y_none():
    assert abm.texto_inicial(None) == ""
    assert abm.texto_inicial(datetime(2026, 1, 2, 3, 4, 5, 999)) == "2026-01-02 03:04:05"
    assert abm.texto_inicial(date(2026, 1, 2)) == "2026-01-02"
    assert r.convertir(abm.texto_inicial(datetime(2026, 1, 2, 3, 4)), r.Campo("f", "datetime", True)) == datetime(2026, 1, 2, 3, 4)
