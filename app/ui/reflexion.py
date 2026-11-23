"""Introspección de los services: a partir de las firmas y los type hints se
describe qué parámetros pide cada método, sin escribir una pantalla por
entidad. Este módulo no importa NiceGUI, así que se puede testear solo."""
import dataclasses
import inspect
import json
import sys
import types
import typing
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal

from app.ui.opciones import opciones_de
from app.ui.referencias import clave_primaria, servicio_referenciado

_VACIO = inspect.Parameter.empty

# Tipos simples soportados; cualquier otro cae en texto libre ("str").
_TIPOS_SIMPLES = {int: "int", float: "float", Decimal: "decimal", str: "str", bool: "bool", datetime: "datetime", date: "date"}


@dataclass
class Campo:
    nombre: str
    tipo: str  # int | float | decimal | str | bool | datetime | date
    requerido: bool
    default: object = None
    nota: str = ""  # ej. "formato AAAA-MM-DD HH:MM"
    subtipo: str = "str"  # solo para tipo "lista": tipo de cada elemento
    opciones: list[str] | None = None  # valores fijos -> desplegable en la UI
    referencia: str | None = None  # clave foránea: nombre del service al que apunta


@dataclass
class Parametro:
    nombre: str
    # Parámetro simple -> `campo`; parámetro dataclass (Cliente, Envio...) -> `campos`.
    campo: Campo | None = None
    campos: list[Campo] = field(default_factory=list)
    clase: type | None = None

    @property
    def es_objeto(self) -> bool:
        return self.clase is not None


_NOTAS = {
    "datetime": "AAAA-MM-DD HH:MM[:SS]",
    "date": "AAAA-MM-DD",
    "lista": "valores separados por coma",
    "json": 'JSON, ej. {"lat": -34.6, "lon": -58.4}',
}


def _desenvolver_optional(anotacion):
    """`X | None` / `Optional[X]` -> (X, True). Cualquier otra cosa -> (a, False)."""
    origen = typing.get_origin(anotacion)
    if origen in (typing.Union, types.UnionType):
        no_none = [a for a in typing.get_args(anotacion) if a is not type(None)]
        if len(no_none) == 1:
            return no_none[0], True
    return anotacion, False


def _tipo_de(anotacion) -> str:
    base, _ = _desenvolver_optional(anotacion)
    origen = typing.get_origin(base) or base
    if origen is list:
        return "lista"
    if origen is dict:
        return "json"
    return _TIPOS_SIMPLES.get(base, "str")


def _subtipo_de(anotacion) -> str:
    """Tipo de los elementos de un `list[X]` (str si no se puede saber)."""
    base, _ = _desenvolver_optional(anotacion)
    args = typing.get_args(base)
    return _TIPOS_SIMPLES.get(args[0], "str") if args else "str"


def _es_dataclass(anotacion) -> bool:
    base, _ = _desenvolver_optional(anotacion)
    return inspect.isclass(base) and dataclasses.is_dataclass(base)


def campos_de_dataclass(clase: type, modulo=None) -> list[Campo]:
    hints = typing.get_type_hints(clase)
    pk = clave_primaria(clase)
    campos = []
    for f in dataclasses.fields(clase):
        anotacion = hints.get(f.name, str)
        _, es_optional = _desenvolver_optional(anotacion)
        tiene_default = f.default is not dataclasses.MISSING or f.default_factory is not dataclasses.MISSING
        if f.default is not dataclasses.MISSING:
            default = f.default
        elif f.default_factory is not dataclasses.MISSING:
            default = f.default_factory()
        else:
            default = None
        tipo = _tipo_de(anotacion)
        campos.append(Campo(
            f.name, tipo, requerido=not (tiene_default or es_optional), default=default,
            nota=_NOTAS.get(tipo, ""), subtipo=_subtipo_de(anotacion),
            opciones=opciones_de(f.name, clase=clase, modulo=modulo) if tipo == "str" else None,
            referencia=servicio_referenciado(f.name) if f.name != pk and tipo in ("int", "str") else None,
        ))
    return campos


def parametros_de(metodo) -> list[Parametro]:
    """Parámetros públicos de un método ya bound (sin `self`)."""
    firma = inspect.signature(metodo)
    try:
        hints = typing.get_type_hints(metodo)
    except Exception:
        hints = {}
    modulo = sys.modules.get(getattr(metodo, "__module__", None))
    resultado = []
    for nombre, p in firma.parameters.items():
        if nombre == "self":  # método tomado de la clase, sin instanciar
            continue
        anotacion = hints.get(nombre, str)
        if _es_dataclass(anotacion):
            clase, _ = _desenvolver_optional(anotacion)
            resultado.append(Parametro(nombre, campos=campos_de_dataclass(clase, modulo), clase=clase))
            continue
        _, es_optional = _desenvolver_optional(anotacion)
        tipo = _tipo_de(anotacion)
        tiene_default = p.default is not _VACIO
        resultado.append(Parametro(
            nombre,
            campo=Campo(nombre, tipo, requerido=not (tiene_default or es_optional),
                        default=p.default if tiene_default else None, nota=_NOTAS.get(tipo, ""),
                        subtipo=_subtipo_de(anotacion),
                        opciones=opciones_de(nombre, modulo=modulo) if tipo == "str" else None,
                        referencia=servicio_referenciado(nombre) if tipo in ("int", "str") else None),
        ))
    return resultado


def nombre_legible(metodo: str) -> str:
    """`listar_por_cliente` -> `Listar por cliente`."""
    texto = metodo.replace("_", " ").strip()
    return texto[:1].upper() + texto[1:]


def descripcion_de(metodo) -> str:
    """Primer párrafo del docstring del método, en una línea ('' si no tiene)."""
    doc = inspect.getdoc(metodo) or ""
    return " ".join(doc.split("\n\n")[0].split())


def metodos_publicos(instancia) -> list[str]:
    return sorted(
        n for n, m in inspect.getmembers(instancia, inspect.ismethod)
        if not n.startswith("_")
    )


def convertir(texto, campo: Campo):
    """Convierte lo tipeado en el formulario al tipo del parámetro.
    Vacío -> None (si es opcional) o ValueError (si es requerido)."""
    if campo.tipo == "bool":
        return bool(texto)
    if texto is None or (isinstance(texto, str) and not texto.strip()):
        if campo.requerido:
            raise ValueError(f"'{campo.nombre}' es obligatorio.")
        return campo.default.copy() if isinstance(campo.default, (list, dict)) else campo.default
    texto = texto.strip() if isinstance(texto, str) else texto
    try:
        if campo.tipo == "lista":
            sub = Campo(campo.nombre, campo.subtipo, requerido=True)
            return [convertir(x, sub) for x in texto.split(",") if x.strip()]
        if campo.tipo == "json":
            valor = json.loads(texto)
            if not isinstance(valor, dict):
                raise ValueError
            return valor
        if campo.tipo == "int":
            return int(texto)
        if campo.tipo == "float":
            return float(str(texto).replace(",", "."))
        if campo.tipo == "decimal":
            return Decimal(str(texto).replace(",", "."))
        if campo.tipo == "datetime":
            return datetime.fromisoformat(texto)
        if campo.tipo == "date":
            return date.fromisoformat(texto)
    except (ValueError, ArithmeticError):  # json.JSONDecodeError es un ValueError
        esperado = campo.nota or campo.tipo
        raise ValueError(f"'{campo.nombre}': valor inválido ({esperado}).") from None
    return texto


def construir_argumentos(parametros: list[Parametro], valores: dict) -> dict:
    """`valores` es {param: texto} o, para dataclasses, {param: {campo: texto}}.
    Devuelve los kwargs listos para llamar al método."""
    kwargs = {}
    for p in parametros:
        if p.es_objeto:
            datos = {c.nombre: convertir(valores.get(p.nombre, {}).get(c.nombre), c) for c in p.campos}
            kwargs[p.nombre] = p.clase(**datos)
        else:
            kwargs[p.nombre] = convertir(valores.get(p.nombre), p.campo)
    return kwargs


def a_filas(resultado) -> list[dict] | None:
    """Normaliza el resultado de un método a filas tabulares, o None si no es
    tabular (None, str, número...)."""
    if dataclasses.is_dataclass(resultado) and not isinstance(resultado, type):
        return [_plano(dataclasses.asdict(resultado))]
    if isinstance(resultado, dict):
        return [_plano(resultado)]
    if isinstance(resultado, (list, tuple)):
        filas = []
        for item in resultado:
            if dataclasses.is_dataclass(item) and not isinstance(item, type):
                filas.append(_plano(dataclasses.asdict(item)))
            elif isinstance(item, dict):
                filas.append(_plano(item))
            else:
                filas.append({"valor": _texto(item)})
        return filas
    return None


def _plano(d: dict) -> dict:
    return {str(k): _texto(v) for k, v in d.items()}


def _texto(v):
    if v is None:
        return ""
    if isinstance(v, (int, float, str, bool)):
        return v
    return str(v)
