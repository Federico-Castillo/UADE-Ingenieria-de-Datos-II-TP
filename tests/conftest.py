import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from mysql.connector import Error as MySQLError

from app.db.mysql import get_cursor, transaction
from app.repositories.alerta_repository import AlertaRepository
from app.repositories.cierre_cuenta_corriente_pagable_repository import CierreCuentaCorrientePagableRepository
from app.repositories.cierre_cuenta_corriente_repository import CierreCuentaCorrienteRepository
from app.repositories.cliente_repository import ClienteRepository
from app.repositories.contenedor_repository import ContenedorRepository
from app.repositories.cuenta_corriente_pagable_repository import CuentaCorrientePagableRepository
from app.repositories.cuenta_corriente_repository import CuentaCorrienteRepository
from app.repositories.envio_contenedor_repository import EnvioContenedorRepository
from app.repositories.envio_repository import EnvioRepository
from app.repositories.evento_logistico_repository import EventoLogisticoRepository
from app.repositories.factura_recibida_repository import FacturaRecibidaRepository
from app.repositories.factura_repository import FacturaRepository
from app.repositories.grupo_trabajo_repository import GrupoTrabajoRepository
from app.repositories.incidente_repository import IncidenteRepository
from app.repositories.lectura_sensor_repository import LecturaSensorRepository
from app.repositories.mensaje_repository import MensajeRepository
from app.repositories.pago_emitido_repository import PagoEmitidoRepository
from app.repositories.pago_repository import PagoRepository
from app.repositories.operador_logistico_repository import OperadorLogisticoRepository
from app.repositories.outbox_repository import OutboxRepository
from app.repositories.prediccion_riesgo_repository import PrediccionRiesgoRepository
from app.repositories.proveedor_repository import ProveedorRepository
from app.repositories.regla_repository import ReglaRepository
from app.repositories.reporte_repository import ReporteRepository
from app.repositories.rol_repository import RolRepository
from app.repositories.sensor_iot_repository import SensorIoTRepository
from app.repositories.sesion_repository import SesionRepository
from app.repositories.tramo_repository import TramoRepository
from app.repositories.usuario_repository import UsuarioRepository
from app.repositories.vehiculo_repository import VehiculoRepository
from app.db.mongo import get_db
from app.db.neo4j_driver import session as neo4j_session

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
def contenedor_repo(mysql_connection) -> ContenedorRepository:
    return ContenedorRepository()


@pytest.fixture
def sensor_iot_repo(mysql_connection) -> SensorIoTRepository:
    return SensorIoTRepository()


@pytest.fixture
def vehiculo_repo(mysql_connection) -> VehiculoRepository:
    return VehiculoRepository()


@pytest.fixture
def envio_repo(mysql_connection) -> EnvioRepository:
    return EnvioRepository()


@pytest.fixture
def envio_contenedor_repo(mysql_connection) -> EnvioContenedorRepository:
    return EnvioContenedorRepository()


@pytest.fixture
def lectura_sensor_repo() -> LecturaSensorRepository:
    return LecturaSensorRepository()


@pytest.fixture
def sensores_cassandra_usados(lectura_sensor_repo):
    """lecturas_sensor particiona por id_sensor: se trackean los id_sensor
    usados en el test y se borra la partición completa al final (más
    eficiente y simple que filtrar por prefijo, que Cassandra no soporta
    bien fuera de la partition key)."""
    usados: list[int] = []
    yield usados
    for id_sensor in usados:
        lectura_sensor_repo._session.execute(
            "DELETE FROM lecturas_sensor WHERE id_sensor = %s", (id_sensor,)
        )


@pytest.fixture
def regla_repo(mysql_connection) -> ReglaRepository:
    return ReglaRepository()


@pytest.fixture
def factura_repo(mysql_connection) -> FacturaRepository:
    return FacturaRepository()


@pytest.fixture
def pago_repo(mysql_connection) -> PagoRepository:
    return PagoRepository()


@pytest.fixture
def cuenta_corriente_repo(mysql_connection) -> CuentaCorrienteRepository:
    return CuentaCorrienteRepository()


@pytest.fixture
def factura_recibida_repo(mysql_connection) -> FacturaRecibidaRepository:
    return FacturaRecibidaRepository()


@pytest.fixture
def pago_emitido_repo(mysql_connection) -> PagoEmitidoRepository:
    return PagoEmitidoRepository()


@pytest.fixture
def cuenta_corriente_pagable_repo(mysql_connection) -> CuentaCorrientePagableRepository:
    return CuentaCorrientePagableRepository()


@pytest.fixture
def outbox_repo(mysql_connection) -> OutboxRepository:
    return OutboxRepository()


@pytest.fixture
def cierre_cuenta_corriente_repo(mysql_connection) -> CierreCuentaCorrienteRepository:
    return CierreCuentaCorrienteRepository()


@pytest.fixture
def cierre_cuenta_corriente_pagable_repo(mysql_connection) -> CierreCuentaCorrientePagableRepository:
    return CierreCuentaCorrientePagableRepository()


@pytest.fixture
def reporte_repo(mysql_connection) -> ReporteRepository:
    return ReporteRepository()


@pytest.fixture
def evento_logistico_repo() -> EventoLogisticoRepository:
    return EventoLogisticoRepository()


@pytest.fixture
def incidente_repo() -> IncidenteRepository:
    return IncidenteRepository()


@pytest.fixture
def mensaje_repo() -> MensajeRepository:
    return MensajeRepository()


@pytest.fixture
def grupo_trabajo_repo() -> GrupoTrabajoRepository:
    return GrupoTrabajoRepository()


@pytest.fixture
def prediccion_riesgo_repo() -> PrediccionRiesgoRepository:
    return PrediccionRiesgoRepository()


@pytest.fixture
def tramo_repo() -> TramoRepository:
    return TramoRepository()


@pytest.fixture
def sesion_repo() -> SesionRepository:
    return SesionRepository()


@pytest.fixture
def alerta_repo() -> AlertaRepository:
    return AlertaRepository()


@pytest.fixture
def sesiones_creadas(sesion_repo):
    """Lista mutable donde el test registra los id_sesion que crea, para
    cerrarlas (y limpiar Redis) automáticamente al final sin esperar el TTL."""
    creadas: list[str] = []
    yield creadas
    for id_sesion in creadas:
        sesion_repo.cerrar(id_sesion)


@pytest.fixture
def alertas_creadas(alerta_repo):
    creadas: list[str] = []
    yield creadas
    for id_alerta in creadas:
        alerta_repo.resolver(id_alerta)


@pytest.fixture(autouse=True)
def limpiar_datos_de_test(mysql_connection):
    def _borrar():
        with transaction() as cursor:
            # outbox_eventos no tiene FK (payload genérico por entidad), pero
            # igual se limpia primero: la subquery necesita que cliente/envio
            # todavía existan para poder encontrar sus eventos.
            cursor.execute(
                "DELETE FROM outbox_eventos WHERE "
                "(entidad = 'cliente' AND id_entidad IN (SELECT id_cliente FROM cliente WHERE razon_social LIKE %s)) OR "
                "(entidad = 'envio' AND id_entidad IN (SELECT id_envio FROM envio WHERE origen LIKE %s))",
                (f"{TEST_PREFIX}%", f"{TEST_PREFIX}%"),
            )
            # Orden por dependencias de FK (hijos antes que padres).
            cursor.execute("DELETE FROM reporte WHERE tipo LIKE %s", (f"{TEST_PREFIX}%",))
            cursor.execute("DELETE FROM regla WHERE nombre LIKE %s", (f"{TEST_PREFIX}%",))
            cursor.execute(
                "DELETE FROM envio_contenedor WHERE "
                "id_envio IN (SELECT id_envio FROM envio WHERE origen LIKE %s) OR "
                "id_contenedor IN (SELECT id_contenedor FROM contenedor WHERE codigo_internacional LIKE %s)",
                (f"{TEST_PREFIX}%", f"{TEST_PREFIX}%"),
            )
            cursor.execute("DELETE FROM envio WHERE origen LIKE %s", (f"{TEST_PREFIX}%",))
            cursor.execute(
                "DELETE FROM sensor_iot WHERE id_contenedor IN "
                "(SELECT id_contenedor FROM contenedor WHERE codigo_internacional LIKE %s)",
                (f"{TEST_PREFIX}%",),
            )
            cursor.execute("DELETE FROM usuario WHERE nombre LIKE %s", (f"{TEST_PREFIX}%",))
            cursor.execute(
                "DELETE FROM pago WHERE id_factura IN "
                "(SELECT id_factura FROM factura WHERE id_cliente IN "
                "(SELECT id_cliente FROM cliente WHERE razon_social LIKE %s))",
                (f"{TEST_PREFIX}%",),
            )
            cursor.execute(
                "DELETE FROM factura WHERE id_cliente IN "
                "(SELECT id_cliente FROM cliente WHERE razon_social LIKE %s)",
                (f"{TEST_PREFIX}%",),
            )
            cursor.execute(
                "DELETE FROM cierre_cuenta_corriente WHERE id_cliente IN "
                "(SELECT id_cliente FROM cliente WHERE razon_social LIKE %s)",
                (f"{TEST_PREFIX}%",),
            )
            cursor.execute(
                "DELETE FROM cuenta_corriente WHERE id_cliente IN "
                "(SELECT id_cliente FROM cliente WHERE razon_social LIKE %s)",
                (f"{TEST_PREFIX}%",),
            )
            cursor.execute("DELETE FROM cliente WHERE razon_social LIKE %s", (f"{TEST_PREFIX}%",))
            cursor.execute("DELETE FROM rol WHERE descripcion LIKE %s", (f"{TEST_PREFIX}%",))
            cursor.execute(
                "DELETE FROM pago_emitido WHERE id_factura_recibida IN "
                "(SELECT id_factura_recibida FROM factura_recibida WHERE "
                "id_proveedor IN (SELECT id_proveedor FROM proveedor WHERE razon_social LIKE %s) OR "
                "id_operador_logistico IN (SELECT id_operador_logistico FROM operador_logistico WHERE razon_social LIKE %s))",
                (f"{TEST_PREFIX}%", f"{TEST_PREFIX}%"),
            )
            cursor.execute(
                "DELETE FROM factura_recibida WHERE "
                "id_proveedor IN (SELECT id_proveedor FROM proveedor WHERE razon_social LIKE %s) OR "
                "id_operador_logistico IN (SELECT id_operador_logistico FROM operador_logistico WHERE razon_social LIKE %s)",
                (f"{TEST_PREFIX}%", f"{TEST_PREFIX}%"),
            )
            cursor.execute(
                "DELETE FROM cuenta_corriente_pagable WHERE "
                "id_proveedor IN (SELECT id_proveedor FROM proveedor WHERE razon_social LIKE %s) OR "
                "id_operador_logistico IN (SELECT id_operador_logistico FROM operador_logistico WHERE razon_social LIKE %s)",
                (f"{TEST_PREFIX}%", f"{TEST_PREFIX}%"),
            )
            cursor.execute(
                "DELETE FROM cierre_cuenta_corriente_pagable WHERE "
                "id_proveedor IN (SELECT id_proveedor FROM proveedor WHERE razon_social LIKE %s) OR "
                "id_operador_logistico IN (SELECT id_operador_logistico FROM operador_logistico WHERE razon_social LIKE %s)",
                (f"{TEST_PREFIX}%", f"{TEST_PREFIX}%"),
            )
            cursor.execute("DELETE FROM proveedor WHERE razon_social LIKE %s", (f"{TEST_PREFIX}%",))
            cursor.execute(
                "DELETE FROM operador_logistico WHERE razon_social LIKE %s", (f"{TEST_PREFIX}%",)
            )
            cursor.execute("DELETE FROM contenedor WHERE codigo_internacional LIKE %s", (f"{TEST_PREFIX}%",))
            cursor.execute("DELETE FROM vehiculo WHERE identificacion LIKE %s", (f"{TEST_PREFIX}%",))

    _borrar()
    yield
    _borrar()


@pytest.fixture(autouse=True)
def limpiar_mongo_de_test():
    def _borrar():
        db = get_db()
        db["eventos_logisticos"].delete_many({"tipo_evento": {"$regex": f"^{TEST_PREFIX}"}})
        # Los eventos de entrega usados por los reportes de tiempos de envío
        # necesitan tipo_evento='entregado' (valor fijo de la convención, no
        # puede llevar el prefijo TEST_), así que se marcan con 'descripcion'.
        db["eventos_logisticos"].delete_many({"descripcion": {"$regex": f"^{TEST_PREFIX}"}})
        db["incidentes"].delete_many({"tipo": {"$regex": f"^{TEST_PREFIX}"}})
        db["mensajes"].delete_many({"contenido": {"$regex": f"^{TEST_PREFIX}"}})
        db["grupos_trabajo"].delete_many({"nombre": {"$regex": f"^{TEST_PREFIX}"}})
        # Los incidentes que dispara el pipeline de LecturaSensor no tienen un
        # "tipo" prefijado con TEST_ (es fijo: "anomalia_{tipo_sensor}"), pero
        # su descripción sí menciona el nombre de la regla que los generó.
        db["incidentes"].delete_many({"descripcion": {"$regex": TEST_PREFIX}})

    _borrar()
    yield
    _borrar()


@pytest.fixture(autouse=True)
def limpiar_neo4j_de_test():
    def _borrar():
        with neo4j_session() as sess:
            sess.run(
                """
                MATCH (c:Cliente) WHERE c.razon_social STARTS WITH $prefix
                OPTIONAL MATCH (c)-[:SOLICITA]->(e:Envio)
                OPTIONAL MATCH (e)-[:INCLUYE]->(t:Tramo)
                OPTIONAL MATCH (t)-[:ORIGEN]->(o:Ubicacion)
                OPTIONAL MATCH (t)-[:DESTINO]->(d:Ubicacion)
                DETACH DELETE c, e, t, o, d
                """,
                prefix=TEST_PREFIX,
            )
            sess.run(
                "MATCH (v:Vehiculo) WHERE v.identificacion STARTS WITH $prefix DETACH DELETE v",
                prefix=TEST_PREFIX,
            )
            sess.run(
                "MATCH (o:Operador) WHERE o.nombre STARTS WITH $prefix DETACH DELETE o", prefix=TEST_PREFIX
            )
            sess.run(
                "MATCH (u:Ubicacion) WHERE u.nombre STARTS WITH $prefix DETACH DELETE u", prefix=TEST_PREFIX
            )

    _borrar()
    yield
    _borrar()


@pytest.fixture
def predicciones_creadas():
    """predicciones_riesgo no tiene un campo string para prefijar con TEST_
    (son todos números), así que se trackean los ids creados y se borran por
    _id al final en vez de por patrón."""
    from bson import ObjectId

    creadas: list[str] = []
    yield creadas
    if creadas:
        get_db()["predicciones_riesgo"].delete_many({"_id": {"$in": [ObjectId(i) for i in creadas]}})
