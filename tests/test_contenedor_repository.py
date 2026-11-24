import pytest

from app.core.exceptions import DuplicateError, RepositoryError
from app.domain.cliente import Cliente
from app.domain.contenedor import Contenedor
from app.domain.envio import Envio
from app.domain.sensor_iot import SensorIoT

pytestmark = pytest.mark.integration


def _contenedor(codigo: str, **kwargs) -> Contenedor:
    defaults = dict(tipo="reefer", capacidad=20.5, estado="disponible")
    defaults.update(kwargs)
    return Contenedor(codigo_internacional=f"{codigo}", **defaults)


def test_crear_y_recuperar_por_id(contenedor_repo):
    id_contenedor = contenedor_repo.crear(_contenedor("TEST_CONT001"))

    recuperado = contenedor_repo.obtener_por_id(id_contenedor)

    assert recuperado is not None
    assert recuperado.codigo_internacional == "TEST_CONT001"
    assert recuperado.capacidad == 20.5


def test_codigo_duplicado_lanza_duplicate_error(contenedor_repo):
    contenedor_repo.crear(_contenedor("TEST_CONT002"))

    with pytest.raises(DuplicateError):
        contenedor_repo.crear(_contenedor("TEST_CONT002"))


def test_actualizar_modifica_los_campos(contenedor_repo):
    id_contenedor = contenedor_repo.crear(_contenedor("TEST_CONT003"))
    contenedor = contenedor_repo.obtener_por_id(id_contenedor)

    contenedor.estado = "en_uso"
    contenedor_repo.actualizar(contenedor)

    recuperado = contenedor_repo.obtener_por_id(id_contenedor)
    assert recuperado.estado == "en_uso"


def test_eliminar_borra_la_fila(contenedor_repo):
    id_contenedor = contenedor_repo.crear(_contenedor("TEST_CONT004"))

    contenedor_repo.eliminar(id_contenedor)

    assert contenedor_repo.obtener_por_id(id_contenedor) is None


def test_eliminar_con_sensores_dice_que_tiene_sensores(contenedor_repo, sensor_iot_repo):
    id_contenedor = contenedor_repo.crear(_contenedor("TEST_CONT005"))
    sensor_iot_repo.crear(SensorIoT(id_contenedor=id_contenedor, tipo="temperatura"))

    with pytest.raises(RepositoryError, match="sensores asociados"):
        contenedor_repo.eliminar(id_contenedor)


def test_eliminar_asignado_a_envio_dice_que_esta_asignado(
    contenedor_repo, cliente_repo, envio_repo, envio_contenedor_repo
):
    id_cliente = cliente_repo.crear(
        Cliente(razon_social="TEST_ClienteElimCont", cuit="90-90000002-2", email="elimcont@example.com")
    )
    id_envio = envio_repo.crear(Envio(id_cliente=id_cliente, origen="TEST_Rosario", destino="Mendoza"))
    id_contenedor = contenedor_repo.crear(_contenedor("TEST_CONT006"))
    envio_contenedor_repo.asignar(id_envio, id_contenedor)

    # Sin sensores: el motivo no es "sensores asociados" (era el mensaje engañoso).
    with pytest.raises(RepositoryError, match="asignado a uno o más envíos"):
        contenedor_repo.eliminar(id_contenedor)
