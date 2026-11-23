"""Detección de capacidades ABM de un service por convención de nombres y
firmas (sin importar NiceGUI, así que se testea solo). Funciona sobre la clase del service (no hace falta instanciarlo, o sea, sin
conectarse a los motores). Un service "es un ABM"
si tiene un listado sin parámetros obligatorios; de ahí en más se habilitan
Nuevo / Editar / Baja según los métodos que encuentre."""
import dataclasses
import json
from dataclasses import dataclass
from datetime import date, datetime

from app.ui import reflexion
from app.ui.referencias import clave_primaria  # noqa: F401 (se reexporta: lo usan la UI y los tests)

_ALTAS = ("dar_alta", "crear", "registrar", "generar", "registrar_pago", "enviar")
_BAJAS = ("dar_baja", "eliminar")

# Entidades que no se dan de baja sino que se CIERRAN cambiando su estado: el
# registro se conserva (un incidente es un hecho que ocurrió). Clave: nombre
# del service; valor: (método que cambia el estado, estado final). Su
# `eliminar` existe solo como compensación del rollback Mongo+Redis y no se
# ofrece como baja en el ABM.
_CIERRES = {"incidente": ("cambiar_estado", "cerrado")}


@dataclass
class Capacidades:
    listar: str | None = None
    alta: str | None = None
    modificar: str | None = None
    baja: str | None = None
    buscar: str | None = None
    cierre: tuple[str, str] | None = None  # (método, estado final) en lugar de baja

    @property
    def es_abm(self) -> bool:
        return self.listar is not None


def _tiene(instancia, nombre: str):
    metodo = getattr(instancia, nombre, None)
    return metodo if callable(metodo) else None


def _sin_obligatorios(metodo) -> bool:
    return all(not p.es_objeto and not p.campo.requerido for p in reflexion.parametros_de(metodo))


def _recibe_dataclass(metodo) -> bool:
    params = reflexion.parametros_de(metodo)
    return bool(params) and params[0].es_objeto


def _recibe_un_id(metodo) -> bool:
    params = reflexion.parametros_de(metodo)
    return len(params) == 1 and not params[0].es_objeto


_PREFIJOS_BAJA = ("dar_baja", "eliminar", "quitar", "cerrar")
_PROCESOS_EN_BLOQUE = {"ejecutar_cierre_mensual", "marcar_inactivos", "procesar_pendientes", "calcular_predicciones"}


def riesgo_de(metodo: str) -> str | None:
    """'baja' si el método borra o da de baja, 'proceso' si modifica datos en
    bloque, None si es inofensivo. La UI pide confirmación en los dos casos."""
    if metodo.startswith(_PREFIJOS_BAJA):
        return "baja"
    if metodo in _PROCESOS_EN_BLOQUE:
        return "proceso"
    return None


def detectar(instancia) -> Capacidades:
    cap = Capacidades()
    listar = _tiene(instancia, "listar")
    if listar is not None and _sin_obligatorios(listar):
        cap.listar = "listar"
    for nombre in _ALTAS:
        m = _tiene(instancia, nombre)
        if m is not None and _recibe_dataclass(m):
            cap.alta = nombre
            break
    m = _tiene(instancia, "modificar")
    if m is not None and _recibe_dataclass(m):
        cap.modificar = "modificar"
    for nombre in _BAJAS:
        m = _tiene(instancia, nombre)
        if m is not None and _recibe_un_id(m):
            cap.baja = nombre
            break
    m = _tiene(instancia, "buscar")
    if m is not None and _recibe_un_id(m):
        cap.buscar = "buscar"
    nombre_clase = instancia.__name__ if isinstance(instancia, type) else type(instancia).__name__
    cierre = _CIERRES.get(nombre_clase.removesuffix("Service").lower())
    if cierre and _tiene(instancia, cierre[0]) is not None:
        cap.cierre, cap.baja = cierre, None
    return cap


def clase_del_alta(instancia, cap: Capacidades) -> type | None:
    for nombre in (cap.modificar, cap.alta):
        if nombre:
            params = reflexion.parametros_de(getattr(instancia, nombre))
            if params and params[0].es_objeto:
                return params[0].clase
    return None


def texto_inicial(valor) -> str:
    """Valor de un atributo -> texto para precargar en un input del formulario."""
    if valor is None:
        return ""
    if isinstance(valor, datetime):
        return valor.isoformat(sep=" ", timespec="seconds")
    if isinstance(valor, date):
        return valor.isoformat()
    if isinstance(valor, (list, tuple)):
        return ",".join(str(x) for x in valor)
    if isinstance(valor, dict):
        return json.dumps(valor, ensure_ascii=False, default=str)
    return str(valor)


def nombre_param_baja(instancia, cap: Capacidades) -> str | None:
    if not cap.baja:
        return None
    return reflexion.parametros_de(getattr(instancia, cap.baja))[0].nombre
