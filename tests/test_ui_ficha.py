"""Ficha 360° del envío: cada sección carga y falla por separado (services falsos, sin DB)."""
from datetime import datetime
from types import SimpleNamespace as NS

import pytest

from app.core.exceptions import NotFoundError, RepositoryError
from app.ui import ficha


@pytest.fixture(autouse=True)
def limpiar_datos_de_test():
    yield


@pytest.fixture(autouse=True)
def limpiar_mongo_de_test():
    yield


@pytest.fixture(autouse=True)
def limpiar_neo4j_de_test():
    yield


def _servicios(**sobre):
    sensor = NS(id_sensor=18, id_contenedor=26, tipo="temperatura")
    base = {
        "envio": NS(obtener_por_id=lambda i: NS(id_envio=i, id_cliente=70)),
        "cliente": NS(obtener_por_id=lambda i: NS(id_cliente=i, razon_social="ACME")),
        "cuenta_corriente": NS(obtener_por_cliente=lambda i: NS(saldo=125.5)),
        "envio_contenedor": NS(listar_contenedores_de_envio=lambda i: [NS(id_contenedor=26)]),
        "sensor_iot": NS(listar_por_contenedor=lambda c: [sensor]),
        "lectura_sensor": NS(ultima_por_sensor=lambda s: NS(temperatura=40.0)),
        "evento_logistico": NS(listar_por_envio=lambda i: [
            NS(fecha_hora=datetime(2026, 1, 3), tipo_evento="b"), NS(fecha_hora=datetime(2026, 1, 1), tipo_evento="a")]),
        "incidente": NS(listar_por_envio=lambda i: [NS(id_incidente="inc1")]),
        "alerta": NS(listar_activas=lambda: [
            NS(id_alerta="x", id_evento="inc1", id_sensor=99),   # por incidente
            NS(id_alerta="y", id_evento=None, id_sensor=18),     # por sensor
            NS(id_alerta="z", id_evento="otro", id_sensor=77)]), # ajena
        "prediccion_riesgo": NS(ultima_por_envio=lambda i: NS(probabilidad_demora=0.7)),
        "tramo": NS(ruta_completa=lambda i: [{"origen": "A", "destino": "B"}]),
    }
    base.update(sobre)
    return lambda nombre: base[nombre]


def test_base_junta_envio_cliente_y_saldo():
    s = ficha.cargar_base(_servicios(), 53)
    assert s.datos["cliente"].razon_social == "ACME" and s.datos["saldo"] == 125.5 and s.motor == "MySQL"


def test_base_tolera_cliente_o_cuenta_ausentes_pero_no_envio_inexistente():
    def sin_cuenta(i):
        raise NotFoundError("sin cuenta")
    s = ficha.cargar_base(_servicios(cuenta_corriente=NS(obtener_por_cliente=sin_cuenta)), 53)
    assert s.datos["saldo"] is None and s.error is None

    def no_existe(i):
        raise NotFoundError("no existe el envío")
    with pytest.raises(NotFoundError):
        ficha.cargar_base(_servicios(envio=NS(obtener_por_id=no_existe)), 999)


def test_contenedores_lecturas_y_eventos_ordenados():
    obtener = _servicios()
    cont = ficha.cargar_contenedores(obtener, 53)
    assert cont.datos[0]["sensores"][0].id_sensor == 18
    lect = ficha.cargar_lecturas(obtener, cont)
    assert lect.motor == "Cassandra" and lect.datos[0][1].temperatura == 40.0
    ev = ficha.cargar_eventos(obtener, 53)
    assert [e.tipo_evento for e in ev.datos] == ["a", "b"]  # cronológico


def test_alertas_filtra_las_del_envio():
    obtener = _servicios()
    inc = ficha.cargar_incidentes(obtener, 53)
    cont = ficha.cargar_contenedores(obtener, 53)
    al = ficha.cargar_alertas(obtener, inc, cont)
    assert sorted(a.id_alerta for a in al.datos) == ["x", "y"]


def test_un_motor_caido_solo_rompe_su_seccion():
    def redis_caido():
        raise RepositoryError("Redis caído")
    obtener = _servicios(alerta=NS(listar_activas=redis_caido))
    inc = ficha.cargar_incidentes(obtener, 53)
    cont = ficha.cargar_contenedores(obtener, 53)
    al = ficha.cargar_alertas(obtener, inc, cont)
    assert al.error == "Redis caído" and al.datos is None
    assert inc.error is None and cont.error is None  # el resto de la ficha sigue


def test_lecturas_sin_contenedores_propaga_el_error_y_vacia():
    cont_mal = ficha.Seccion("contenedores", "x", "MySQL", error="MySQL caído")
    assert ficha.cargar_lecturas(_servicios(), cont_mal).error
    vacia = ficha.cargar_contenedores(_servicios(envio_contenedor=NS(listar_contenedores_de_envio=lambda i: [])), 53)
    assert vacia.vacia and not vacia.error
    assert ficha.cargar_lecturas(_servicios(), vacia).vacia
