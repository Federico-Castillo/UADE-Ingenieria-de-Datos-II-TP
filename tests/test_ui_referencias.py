"""Claves foráneas como desplegables: detección del service referenciado y
etiquetas de las opciones (sin DB ni NiceGUI)."""
from dataclasses import dataclass

import pytest

from app.ui import referencias as ref
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


@pytest.mark.parametrize("campo,esperado", [
    ("id_cliente", "cliente"),
    ("id_envio", "envio"),
    ("id_operador_logistico", "operador_logistico"),
    ("id_factura_recibida", "factura_recibida"),  # gana el nombre más largo, no "factura"
    ("id_factura", "factura"),
    ("id_usuario_creador", "usuario"),             # prefijo
    ("id_usuario_a", "usuario"),
    ("id_sensor", "sensor_iot"),                   # alias
    ("id_grupo", "grupo_trabajo"),
    ("id_remitente", "usuario"),
    ("id_destinatario", "usuario"),
    ("razon_social", None),                        # no es id_*
    ("id_inexistente", None),
])
def test_servicio_referenciado(campo, esperado):
    assert ref.servicio_referenciado(campo) == esperado


@dataclass
class _Cli:
    razon_social: str
    email: str
    id_cliente: int | None = None


@dataclass
class _Env:
    origen: str
    destino: str
    id_envio: int | None = None


@dataclass
class _SinDescripcion:
    id_x: int | None = None


def test_etiquetas_y_opciones_ordenadas_por_pk():
    assert ref.etiqueta_de(_Cli("ACME SA", "a@b.com", 70)) == "70 · ACME SA · a@b.com"
    assert ref.etiqueta_de(_Env("BA", "Madrid", 5)) == "5 · BA · Madrid"
    assert ref.etiqueta_de(_SinDescripcion(9)) == "9"
    opciones = ref.opciones_de_objetos([_Cli("B", "b@x", 71), _Cli("A", "a@x", 70), _Cli("N", "n@x", None)])
    assert [v for v, _ in opciones] == [70, 71]  # sin PK se ignora; ordenado por PK


@dataclass
class _Fac:
    id_cliente: int
    estado: str = "pagada"
    id_factura: int | None = None


@dataclass
class _Inc:
    tipo: str
    id_incidente: str | None = None


def test_etiqueta_completa_con_fk_y_acorta_object_id():
    assert ref.etiqueta_de(_Fac(70, "pagada", 14)) == "14 · pagada · cliente 70"
    assert ref.etiqueta_de(_Inc("anomalia_humedad", "6ae1082686860c34960c833a")).startswith("…0c833a · anomalia_humedad")


def test_pk_propia_no_es_referencia_y_las_fk_si():
    from app.services.envio_service import EnvioService
    from app.services.mensaje_service import MensajeService
    from app.services.tramo_service import TramoService

    (envio,) = r.parametros_de(EnvioService.dar_alta)
    campos = {c.nombre: c for c in envio.campos}
    assert campos["id_cliente"].referencia == "cliente"
    assert campos["id_envio"].referencia is None   # la PK del propio envío no apunta a nada
    assert campos["origen"].referencia is None

    (mensaje,) = r.parametros_de(MensajeService.enviar)
    campos = {c.nombre: c for c in mensaje.campos}
    assert campos["id_remitente"].referencia == "usuario"
    assert campos["id_grupo"].referencia == "grupo_trabajo"

    (tramo,) = r.parametros_de(TramoService.registrar_tramo)
    campos = {c.nombre: c for c in tramo.campos}
    assert (campos["id_envio"].referencia, campos["id_vehiculo"].referencia,
            campos["id_operador_logistico"].referencia) == ("envio", "vehiculo", "operador_logistico")


def test_parametros_simples_tambien_son_referencia():
    from app.services.factura_service import FacturaService

    (p,) = r.parametros_de(FacturaService.listar_por_cliente)
    assert p.campo.referencia == "cliente"
    (q,) = r.parametros_de(FacturaService.dar_alta)
    assert {c.nombre: c.referencia for c in q.campos}["importe_total"] is None
