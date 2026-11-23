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


# ---------- el incidente se cierra, no se borra ----------

def test_incidente_se_cierra_en_vez_de_darse_de_baja():
    from app.services.incidente_service import IncidenteService

    cap = abm.detectar(IncidenteService)
    assert cap.es_abm and cap.alta == "registrar"
    assert cap.baja is None                      # su `eliminar` es solo la compensación del rollback
    assert cap.cierre == ("cambiar_estado", "cerrado")


def test_otras_entidades_conservan_su_baja_y_no_tienen_cierre():
    from app.services.cliente_service import ClienteService
    from app.services.vehiculo_service import VehiculoService

    assert abm.detectar(ClienteService).baja == "dar_baja" and abm.detectar(ClienteService).cierre is None
    assert abm.detectar(VehiculoService).baja == "eliminar" and abm.detectar(VehiculoService).cierre is None


# ---------- campos que la UI nunca pide ----------

def test_password_hash_es_interno_y_el_alta_de_usuario_no_lo_necesita():
    from app.services.usuario_service import UsuarioService

    assert "password_hash" in abm.CAMPOS_INTERNOS
    params = r.parametros_de(UsuarioService.dar_alta)
    usuario, password = params[0], params[1]
    assert "password_hash" in {c.nombre for c in usuario.campos}  # sigue en el dataclass, solo la UI lo oculta
    valores = {c.nombre: "" for c in usuario.campos if c.nombre != "password_hash"}  # el formulario no lo envía
    valores.update({"nombre": "Ana", "apellido": "Perez", "email": "a@b.com", "id_rol": "1", "estado": "activo"})
    kwargs = r.construir_argumentos(params, {"usuario": valores, "password": "Clave123"})
    assert kwargs["usuario"].password_hash == "" and kwargs["password"] == "Clave123"
