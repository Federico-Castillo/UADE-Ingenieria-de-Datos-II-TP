"""Verifica el pipeline completo que describe el desafío de complejidad
adicional: una lectura anómala en Cassandra dispara un Incidente en MongoDB
(resolviendo id_envio vía sensor -> contenedor -> envio_contenedor) y una
Alerta en Redis vinculada a ese incidente."""
import pytest

from app.domain.cliente import Cliente
from app.domain.contenedor import Contenedor
from app.domain.envio import Envio
from app.domain.lectura_sensor import LecturaSensor
from app.domain.regla import Regla
from app.domain.rol import Rol
from app.domain.sensor_iot import SensorIoT
from app.domain.usuario import Usuario
from app.services.alerta_service import AlertaService
from app.services.incidente_service import IncidenteService
from app.services.lectura_sensor_service import LecturaSensorService

pytestmark = pytest.mark.integration


@pytest.fixture
def contexto_pipeline(
    cliente_repo, envio_repo, contenedor_repo, envio_contenedor_repo,
    sensor_iot_repo, rol_repo, usuario_repo, regla_repo,
):
    id_cliente = cliente_repo.crear(
        Cliente(razon_social="TEST_ClientePipeline", cuit="90-91000001-1", email="pipeline1@example.com")
    )
    id_envio = envio_repo.crear(Envio(id_cliente=id_cliente, origen="TEST_Pipeline", destino="Destino"))
    id_contenedor = contenedor_repo.crear(
        Contenedor(codigo_internacional="TEST_PIPELINE001", tipo="reefer", capacidad=12.0)
    )
    envio_contenedor_repo.asignar(id_envio, id_contenedor)
    id_sensor = sensor_iot_repo.crear(SensorIoT(id_contenedor=id_contenedor, tipo="temperatura"))
    id_rol = rol_repo.crear(Rol(descripcion="TEST_RolPipeline"))
    id_usuario = usuario_repo.crear(
        Usuario(
            nombre="TEST_UsuarioPipeline",
            apellido="Apellido",
            email="pipeline2@example.com",
            id_rol=id_rol,
            password_hash="hash-de-prueba",
        )
    )
    id_regla = regla_repo.crear(
        Regla(
            nombre="TEST_ReglaPipeline",
            tipo_sensor="temperatura",
            operador_comparacion=">",
            valor_umbral=30.0,
            severidad="critica",
            id_usuario_creador=id_usuario,
        )
    )
    return id_envio, id_sensor, id_regla


def test_lectura_normal_no_dispara_nada(contexto_pipeline, lectura_sensor_repo, sensores_cassandra_usados):
    id_envio, id_sensor, _ = contexto_pipeline
    sensores_cassandra_usados.append(id_sensor)

    service = LecturaSensorService(repository=lectura_sensor_repo)
    service.registrar_lectura(LecturaSensor(id_sensor=id_sensor, temperatura=20.0))

    incidentes = IncidenteService().listar_por_envio(id_envio)
    assert incidentes == []


def test_lectura_anomala_dispara_incidente_y_alerta(
    contexto_pipeline, lectura_sensor_repo, sensores_cassandra_usados, alertas_creadas
):
    id_envio, id_sensor, id_regla = contexto_pipeline
    sensores_cassandra_usados.append(id_sensor)

    service = LecturaSensorService(repository=lectura_sensor_repo)
    service.registrar_lectura(LecturaSensor(id_sensor=id_sensor, temperatura=38.0))

    # Puede haber otras Reglas activas de tipo 'temperatura' en la base (ej.
    # datos de prueba de scripts/seed_datos_prueba.py) que también disparen
    # con este valor: se filtra por la propia regla en vez de asumir que es
    # la única activa de ese tipo_sensor.
    incidentes = [
        i for i in IncidenteService().listar_por_envio(id_envio) if "TEST_ReglaPipeline" in i.descripcion
    ]
    assert len(incidentes) == 1
    incidente = incidentes[0]
    assert incidente.tipo == "anomalia_temperatura"
    assert incidente.severidad == "critica"

    alertas_del_sensor = [a for a in AlertaService().listar_activas() if a.id_sensor == id_sensor]
    alertas_creadas.extend(a.id_alerta for a in alertas_del_sensor)
    alertas_propias = [a for a in alertas_del_sensor if a.id_regla == id_regla]
    assert len(alertas_propias) == 1
    alerta = alertas_propias[0]
    assert alerta.id_evento == incidente.id_incidente
