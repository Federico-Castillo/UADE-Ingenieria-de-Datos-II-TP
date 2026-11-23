"""Campos que son claves foráneas (`id_cliente`, `id_envio`...): a qué service
apuntan y cómo se muestran como opciones de un desplegable en vez de pedir el
número a mano. Sin NiceGUI ni acceso a datos, así que se testea solo; el
armado de opciones con datos reales lo hace la UI.

Convención: `id_<x>` apunta al service `<x>_service` (el nombre más largo que
sea prefijo gana: `id_usuario_creador` -> usuario, `id_factura_recibida` ->
factura_recibida). Unas pocas excepciones de nombre están en `_ALIAS`."""
import dataclasses
import pkgutil
from functools import lru_cache

import app.services as _paquete

# base del campo (sin "id_") -> service, cuando no coincide con el nombre.
_ALIAS = {
    "sensor": "sensor_iot",
    "grupo": "grupo_trabajo",
    "remitente": "usuario",
    "destinatario": "usuario",
}

# Atributos que mejor describen un registro, en orden de preferencia.
_DESCRIPTIVOS = (
    "razon_social", "nombre", "apellido", "codigo_internacional", "identificacion",
    "email", "origen", "destino", "tipo", "descripcion", "estado",
)
_MAX_PARTES = 2
_MAX_TEXTO = 40


@lru_cache(maxsize=1)
def _servicios() -> tuple[str, ...]:
    nombres = [i.name.removesuffix("_service") for i in pkgutil.iter_modules(_paquete.__path__)
               if i.name.endswith("_service")]
    return tuple(sorted(nombres, key=len, reverse=True))  # los más largos primero


def clave_primaria(clase: type) -> str | None:
    """Convención del proyecto: la PK es el último campo del dataclass, se llama
    id_* y es opcional (None hasta que la DB la asigna)."""
    campos = dataclasses.fields(clase)
    if not campos:
        return None
    ultimo = campos[-1]
    if ultimo.name.startswith("id_") and ultimo.default is None:
        return ultimo.name
    return None


def servicio_referenciado(nombre_campo: str) -> str | None:
    """`id_cliente` -> 'cliente'; un campo que no empieza con id_ o sin service
    que coincida -> None."""
    if not nombre_campo.startswith("id_"):
        return None
    base = nombre_campo[3:]
    if base in _ALIAS:
        return _ALIAS[base]
    for servicio in _servicios():
        if base == servicio or base.startswith(servicio + "_"):
            return servicio
    return None


def _id_corto(valor) -> str:
    """Los ObjectId de Mongo (24 hex) se acortan a '…ultimos6' para no ensuciar el desplegable."""
    texto = str(valor)
    return "…" + texto[-6:] if len(texto) > 12 else texto


def etiqueta_de(obj) -> str:
    """'70 · Agropecuaria del Sur · demo@x.com' a partir de los atributos
    descriptivos; si el registro casi no tiene texto (ej. una factura) se
    completa con su clave foránea ('14 · pagada · cliente 70')."""
    pk = clave_primaria(type(obj)) if dataclasses.is_dataclass(obj) else None
    partes = []
    for atributo in _DESCRIPTIVOS:
        valor = getattr(obj, atributo, None)
        if isinstance(valor, str) and valor.strip():
            partes.append(valor.strip()[:_MAX_TEXTO])
        if len(partes) == _MAX_PARTES:
            break
    if len(partes) < _MAX_PARTES and dataclasses.is_dataclass(obj):
        for f in dataclasses.fields(obj):
            valor = getattr(obj, f.name, None)
            if f.name.startswith("id_") and f.name != pk and valor is not None:
                partes.append(f"{f.name[3:].replace('_', ' ')} {_id_corto(valor)}")
                break
    identificador = _id_corto(getattr(obj, pk, "?")) if pk else "?"
    return " · ".join([identificador, *partes])


def opciones_de_objetos(objetos) -> list[tuple[object, str]]:
    """[(valor_de_la_PK, etiqueta)] ordenado por PK; ignora lo que no tenga PK."""
    resultado = []
    for obj in objetos:
        pk = clave_primaria(type(obj)) if dataclasses.is_dataclass(obj) else None
        valor = getattr(obj, pk, None) if pk else None
        if valor is not None:
            resultado.append((valor, etiqueta_de(obj)))
    return sorted(resultado, key=lambda par: (str(type(par[0])), par[0]))
