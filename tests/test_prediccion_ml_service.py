"""Tests de PrediccionMLService. Las validaciones de negocio (mínimo de
muestras, una sola clase) se prueban con repositorios falsos -- son
agregaciones GLOBALES sobre todos los envíos, así que no se pueden aislar de
forma confiable contra la base real compartida (puede haber datos de otras
tandas/demo). El camino feliz de punta a punta sí se prueba contra la base
real, al final de este archivo."""
import pytest

from app.core.exceptions import ValidationError
from app.domain.cliente import Cliente
from app.domain.envio import Envio
from app.services.prediccion_ml_service import PrediccionMLService
from app.services.prediccion_riesgo_service import PrediccionRiesgoService


class _FakeEnvioRepo:
    def __init__(self, envios):
        self._envios = envios

    def listar(self):
        return self._envios


class _FakeIncidenteRepo:
    def __init__(self, incidentes=None):
        self._incidentes = incidentes or []

    def listar(self):
        return self._incidentes


class _FakeTramoRepo:
    def medio_transporte_principal_por_envio(self):
        return {}


class _FakePrediccionService:
    def __init__(self):
        self.registrados = []

    def registrar(self, prediccion):
        prediccion.id_prediccion = f"fake-{len(self.registrados)}"
        self.registrados.append(prediccion)
        return prediccion


def _envio(id_envio, id_cliente, estado, prioridad="normal"):
    return Envio(
        id_cliente=id_cliente, origen="X", destino="Y", estado=estado, prioridad=prioridad, id_envio=id_envio
    )


def _service(envios, incidentes=None, prediccion_service=None):
    return PrediccionMLService(
        envio_repo=_FakeEnvioRepo(envios),
        incidente_repo=_FakeIncidenteRepo(incidentes),
        tramo_repo=_FakeTramoRepo(),
        prediccion_service=prediccion_service or _FakePrediccionService(),
    )


def test_lanza_error_si_no_hay_suficientes_envios_resueltos():
    envios = [_envio(1, 1, "entregado"), _envio(2, 1, "demorado")]

    with pytest.raises(ValidationError):
        _service(envios).calcular_predicciones()


def test_lanza_error_si_todos_los_resueltos_son_de_la_misma_clase():
    envios = [_envio(i, 1, "entregado") for i in range(1, 6)]

    with pytest.raises(ValidationError):
        _service(envios).calcular_predicciones()


def test_sin_envios_para_predecir_devuelve_lista_vacia():
    envios = [
        _envio(1, 1, "entregado"), _envio(2, 1, "demorado"),
        _envio(3, 1, "entregado"), _envio(4, 1, "demorado"),
    ]

    resultado = _service(envios).calcular_predicciones()

    assert resultado == []


def test_predice_y_persiste_para_envios_pendientes():
    prediccion_service = _FakePrediccionService()
    envios = [
        _envio(1, 1, "entregado", prioridad="baja"),
        _envio(2, 1, "demorado", prioridad="urgente"),
        _envio(3, 2, "entregado", prioridad="normal"),
        _envio(4, 2, "demorado", prioridad="urgente"),
        _envio(5, 1, "pendiente", prioridad="normal"),
    ]

    resultado = _service(envios, prediccion_service=prediccion_service).calcular_predicciones()

    assert len(resultado) == 1
    assert resultado[0].id_envio == 5
    assert 0.0 <= resultado[0].probabilidad_demora <= 1.0
    assert resultado[0].features_entrada["origen"] == "scikit-learn"
    assert prediccion_service.registrados == resultado


@pytest.mark.integration
def test_calcular_predicciones_de_punta_a_punta(cliente_repo, envio_repo, predicciones_creadas):
    id_cliente = cliente_repo.crear(
        Cliente(razon_social="TEST_ClientePrediccionML", cuit="90-98000001-1", email="prediccionml1@example.com")
    )
    envio_repo.crear(Envio(id_cliente=id_cliente, origen="TEST_A", destino="TEST_B", estado="entregado"))
    envio_repo.crear(Envio(id_cliente=id_cliente, origen="TEST_A", destino="TEST_B", estado="demorado"))
    envio_repo.crear(Envio(id_cliente=id_cliente, origen="TEST_A", destino="TEST_B", estado="entregado"))
    envio_repo.crear(Envio(id_cliente=id_cliente, origen="TEST_A", destino="TEST_B", estado="demorado"))
    id_envio_a_predecir = envio_repo.crear(
        Envio(id_cliente=id_cliente, origen="TEST_A", destino="TEST_B", estado="pendiente")
    )

    resultado = PrediccionMLService().calcular_predicciones()
    # calcular_predicciones() corre sobre TODOS los envíos pendientes/en
    # tránsito del sistema (no solo el de este test), así que se trackean
    # todas las predicciones creadas para no dejar residuos de la corrida.
    predicciones_creadas.extend(p.id_prediccion for p in resultado)

    fila = next(p for p in resultado if p.id_envio == id_envio_a_predecir)
    assert 0.0 <= fila.probabilidad_demora <= 1.0
    assert fila.id_prediccion is not None

    guardada = PrediccionRiesgoService().ultima_por_envio(id_envio_a_predecir)
    assert guardada is not None
    assert guardada.id_prediccion == fila.id_prediccion
