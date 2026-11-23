"""Datos de la ficha 360° de un envío: junta, en una sola vista, lo que vive en
los 5 motores. Cada sección se carga por separado y falla por separado: si un
motor está caído, esa sección muestra su error y el resto de la ficha sigue.

`obtener` es una función `nombre_de_service -> instancia` (el RegistroServices
de la UI), así que acá no hay NiceGUI y se testea con services falsos."""
import logging
from dataclasses import dataclass
from typing import Callable

logger = logging.getLogger(__name__)


@dataclass
class Seccion:
    clave: str
    titulo: str
    motor: str
    datos: object = None
    error: str | None = None

    @property
    def vacia(self) -> bool:
        return self.error is None and not self.datos


def _cargar(clave: str, titulo: str, motor: str, funcion: Callable[[], object]) -> Seccion:
    try:
        return Seccion(clave, titulo, motor, datos=funcion())
    except Exception as e:  # un motor caído o un dato roto solo afecta a su sección
        logger.exception("No se pudo cargar la sección '%s' de la ficha del envío", clave)
        return Seccion(clave, titulo, motor, error=str(e) or type(e).__name__)


def cargar_base(obtener, id_envio: int) -> Seccion:
    """Envío + cliente + saldo de su cuenta corriente (MySQL). Si el envío no
    existe lanza NotFoundError: sin envío no hay ficha."""
    envio = obtener("envio").obtener_por_id(id_envio)

    def _cliente():
        try:
            return obtener("cliente").obtener_por_id(envio.id_cliente)
        except Exception:
            logger.exception("No se pudo leer el cliente %s", envio.id_cliente)
            return None

    def _saldo():
        try:
            return obtener("cuenta_corriente").obtener_por_cliente(envio.id_cliente).saldo
        except Exception:
            return None  # un cliente puede no tener cuenta corriente todavía

    return Seccion("base", "Envío y cliente", "MySQL",
                   datos={"envio": envio, "cliente": _cliente(), "saldo": _saldo()})


def cargar_contenedores(obtener, id_envio: int) -> Seccion:
    """[{'contenedor': Contenedor, 'sensores': [SensorIoT]}] (MySQL, relación N:M)."""
    def _f():
        contenedores = obtener("envio_contenedor").listar_contenedores_de_envio(id_envio)
        sensores = obtener("sensor_iot")
        return [{"contenedor": c, "sensores": sensores.listar_por_contenedor(c.id_contenedor)} for c in contenedores]
    return _cargar("contenedores", "Contenedores y sensores", "MySQL", _f)


def cargar_lecturas(obtener, contenedores: Seccion) -> Seccion:
    """[(SensorIoT, última LecturaSensor | None)] (Cassandra)."""
    def _f():
        if contenedores.error:
            raise RuntimeError("No se pudieron leer los contenedores del envío.")
        servicio = obtener("lectura_sensor")
        return [(s, servicio.ultima_por_sensor(s.id_sensor))
                for item in contenedores.datos or [] for s in item["sensores"]]
    return _cargar("lecturas", "Última lectura de cada sensor", "Cassandra", _f)


def cargar_eventos(obtener, id_envio: int) -> Seccion:
    def _f():
        eventos = obtener("evento_logistico").listar_por_envio(id_envio)
        return sorted(eventos, key=lambda e: (e.fecha_hora is None, e.fecha_hora))
    return _cargar("eventos", "Eventos logísticos", "MongoDB", _f)


def cargar_incidentes(obtener, id_envio: int) -> Seccion:
    return _cargar("incidentes", "Incidentes", "MongoDB", lambda: obtener("incidente").listar_por_envio(id_envio))


def cargar_riesgo(obtener, id_envio: int) -> Seccion:
    return _cargar("riesgo", "Predicción de riesgo de atraso", "MongoDB",
                   lambda: obtener("prediccion_riesgo").ultima_por_envio(id_envio))


def cargar_ruta(obtener, id_envio: int) -> Seccion:
    return _cargar("ruta", "Ruta y tramos", "Neo4j", lambda: obtener("tramo").ruta_completa(id_envio))


def cargar_alertas(obtener, incidentes: Seccion, contenedores: Seccion) -> Seccion:
    """Alertas activas (Redis) que pertenecen a este envío: las que apuntan a
    uno de sus incidentes o nacieron de uno de los sensores de sus contenedores."""
    def _f():
        ids_incidente = {i.id_incidente for i in (incidentes.datos or [])}
        ids_sensor = {s.id_sensor for item in (contenedores.datos or []) for s in item["sensores"]}
        if incidentes.error and contenedores.error:
            raise RuntimeError("Sin incidentes ni sensores del envío no se puede relacionar ninguna alerta.")
        return [a for a in obtener("alerta").listar_activas()
                if a.id_evento in ids_incidente or a.id_sensor in ids_sensor]
    return _cargar("alertas", "Alertas activas", "Redis", _f)
