import pytest

from app.core.exceptions import ValidationError
from app.domain.cliente import Cliente
from app.domain.envio import Envio
from app.domain.operador_logistico import OperadorLogistico
from app.domain.tramo import Tramo
from app.domain.vehiculo import Vehiculo
from app.services.tramo_service import TramoService

pytestmark = pytest.mark.integration


@pytest.fixture
def contexto_envio(cliente_repo, envio_repo, vehiculo_repo, operador_logistico_repo):
    """Arma un envío + vehículo + operador reales en MySQL, necesarios para
    que TramoService pueda proyectar los nodos livianos en Neo4j."""
    id_cliente = cliente_repo.crear(
        Cliente(razon_social="TEST_ClienteTramo", cuit="90-80000001-1", email="tramo1@example.com")
    )
    id_envio = envio_repo.crear(Envio(id_cliente=id_cliente, origen="TEST_BuenosAires", destino="Mendoza"))
    id_vehiculo = vehiculo_repo.crear(
        Vehiculo(tipo="camion", identificacion="TEST_TRAMO001", empresa_operadora="TEST_Transportes")
    )
    id_operador = operador_logistico_repo.crear(
        OperadorLogistico(razon_social="TEST_OperadorTramo", cuit="90-80000002-1", email="tramo2@example.com")
    )
    return id_envio, id_vehiculo, id_operador


def _tramo(id_envio: int, id_vehiculo: int, id_operador: int, origen: str, destino: str) -> Tramo:
    return Tramo(
        id_envio=id_envio,
        medio_transporte="terrestre",
        id_vehiculo=id_vehiculo,
        id_operador_logistico=id_operador,
        origen_nombre=f"TEST_{origen}",
        destino_nombre=f"TEST_{destino}",
    )


def test_registrar_tramo_asigna_orden_1(tramo_repo, contexto_envio):
    id_envio, id_vehiculo, id_operador = contexto_envio
    service = TramoService(repository=tramo_repo)

    tramo = service.registrar_tramo(_tramo(id_envio, id_vehiculo, id_operador, "Origen1", "Destino1"))

    assert tramo.id_tramo is not None
    assert tramo.orden == 1


def test_segundo_tramo_del_mismo_envio_queda_en_orden_2(tramo_repo, contexto_envio):
    id_envio, id_vehiculo, id_operador = contexto_envio
    service = TramoService(repository=tramo_repo)

    service.registrar_tramo(_tramo(id_envio, id_vehiculo, id_operador, "A", "B"))
    tramo2 = service.registrar_tramo(_tramo(id_envio, id_vehiculo, id_operador, "B", "C"))

    assert tramo2.orden == 2


def test_ruta_completa_devuelve_los_tramos_en_orden(tramo_repo, contexto_envio):
    id_envio, id_vehiculo, id_operador = contexto_envio
    service = TramoService(repository=tramo_repo)
    service.registrar_tramo(_tramo(id_envio, id_vehiculo, id_operador, "Inicio", "Medio"))
    service.registrar_tramo(_tramo(id_envio, id_vehiculo, id_operador, "Medio", "Fin"))

    ruta = service.ruta_completa(id_envio)

    assert len(ruta) == 2
    assert ruta[0]["orden"] == 1
    assert ruta[0]["origen"] == "TEST_Inicio"
    assert ruta[1]["orden"] == 2
    assert ruta[1]["destino"] == "TEST_Fin"


def test_red_relaciones_incluye_cliente_y_operador(tramo_repo, contexto_envio, cliente_repo, operador_logistico_repo):
    id_envio, id_vehiculo, id_operador = contexto_envio
    service = TramoService(repository=tramo_repo)
    service.registrar_tramo(_tramo(id_envio, id_vehiculo, id_operador, "X", "Y"))

    red = service.red_relaciones()

    assert any(
        r["id_operador_logistico"] == id_operador and r["cliente"] == "TEST_ClienteTramo" for r in red
    )


def test_registrar_tramo_rechaza_envio_inexistente(tramo_repo):
    service = TramoService(repository=tramo_repo)

    with pytest.raises(ValidationError):
        service.registrar_tramo(_tramo(999999999, 1, 1, "A", "B"))


def test_tramo_con_costo_aparece_en_costos_por_medio_transporte(tramo_repo, contexto_envio):
    id_envio, id_vehiculo, id_operador = contexto_envio
    service = TramoService(repository=tramo_repo)
    tramo = _tramo(id_envio, id_vehiculo, id_operador, "CostoA", "CostoB")
    tramo.costo = 1500.0

    antes = {f["medio_transporte"]: f for f in service.costos_por_medio_transporte()}
    service.registrar_tramo(tramo)
    despues = {f["medio_transporte"]: f for f in service.costos_por_medio_transporte()}

    cantidad_antes = antes.get("terrestre", {}).get("cantidad_tramos", 0)
    total_antes = antes.get("terrestre", {}).get("costo_total", 0.0)
    assert despues["terrestre"]["cantidad_tramos"] == cantidad_antes + 1
    assert despues["terrestre"]["costo_total"] == pytest.approx(total_antes + 1500.0)


def test_tramo_sin_costo_no_se_cuenta_en_costos_por_medio_transporte(tramo_repo, contexto_envio):
    id_envio, id_vehiculo, id_operador = contexto_envio
    service = TramoService(repository=tramo_repo)
    antes = {f["medio_transporte"]: f["cantidad_tramos"] for f in service.costos_por_medio_transporte()}

    service.registrar_tramo(_tramo(id_envio, id_vehiculo, id_operador, "SinCostoA", "SinCostoB"))

    despues = {f["medio_transporte"]: f["cantidad_tramos"] for f in service.costos_por_medio_transporte()}
    assert despues.get("terrestre", 0) == antes.get("terrestre", 0)


def test_costo_negativo_lanza_validation_error(tramo_repo, contexto_envio):
    id_envio, id_vehiculo, id_operador = contexto_envio
    service = TramoService(repository=tramo_repo)
    tramo = _tramo(id_envio, id_vehiculo, id_operador, "Neg1", "Neg2")
    tramo.costo = -5.0

    with pytest.raises(ValidationError):
        service.registrar_tramo(tramo)
