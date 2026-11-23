"""De dónde salen los desplegables de los formularios: nunca se hardcodean
listas nuevas, se reutilizan las que el proyecto ya define.

  1. Constantes `_XXX_VALIDOS/_VALIDAS` del módulo del service (las mismas
     que usa la validación): `_PRIORIDADES_VALIDAS` -> campo `prioridad`.
  2. Columnas ENUM del esquema de MySQL (tabla = nombre del dataclass en
     snake_case): `cliente.estado`, `regla.operador_comparacion`...
  3. Los tipos de sensor de `CAMPO_POR_TIPO_SENSOR`, que es el mapeo que
     comparten el service y el simulador.
  4. Unos pocos valores sin otra fuente (estado de Envío), documentados acá.

Sin fuente conocida el campo queda como texto libre."""
import os
import re
from functools import lru_cache

from app.domain.lectura_sensor import CAMPO_POR_TIPO_SENSOR

_SCHEMA_MYSQL = os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "schema", "mysql_schema.sql")
_SUFIJO = re.compile(r"^_?(?P<base>[A-Z_]+?)_VALID[OA]S$")

_TIPOS_SENSOR = list(CAMPO_POR_TIPO_SENSOR)

# (Dataclass, campo) -> opciones. Estados de Envío: los que usa el resto del
# código (reportes y predicción) y los que carga el seed; no hay constante.
_MANUALES = {
    ("SensorIoT", "tipo"): _TIPOS_SENSOR,
    ("Regla", "tipo_sensor"): _TIPOS_SENSOR,
    ("Envio", "estado"): ["pendiente", "en_transito", "entregado", "demorado", "cancelado"],
}


def _snake(nombre: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", nombre).lower()


@lru_cache(maxsize=None)
def _enums_mysql() -> dict[tuple[str, str], list[str]]:
    try:
        with open(_SCHEMA_MYSQL, encoding="utf-8") as f:
            texto = f.read()
    except OSError:
        return {}
    resultado: dict[tuple[str, str], list[str]] = {}
    for tabla, cuerpo in re.findall(r"CREATE TABLE\s+(?:IF NOT EXISTS\s+)?(\w+)\s*\((.*?)\n\)\s*;", texto, re.S):
        for columna, valores in re.findall(r"(\w+)\s+ENUM\(([^)]*)\)", cuerpo):
            resultado[(tabla, columna)] = re.findall(r"'([^']*)'", valores)
    return resultado


def _constantes_modulo(modulo) -> dict[str, list[str]]:
    """{base_singular_candidata: valores} a partir de las `_XXX_VALIDOS` del módulo."""
    resultado: dict[str, list[str]] = {}
    for nombre, valor in vars(modulo).items():
        m = _SUFIJO.match(nombre)
        if not m or not isinstance(valor, (set, frozenset, tuple, list)):
            continue
        if not all(isinstance(v, str) for v in valor):
            continue
        base = m.group("base").lower()
        for singular in (base[:-2], base[:-1]):  # prioridades->prioridad, estados->estado
            resultado[singular] = sorted(valor)
    return resultado


def opciones_de(nombre_campo: str, *, clase=None, modulo=None) -> list[str] | None:
    if clase is not None:
        manual = _MANUALES.get((clase.__name__, nombre_campo))
        if manual:
            return list(manual)
        enum = _enums_mysql().get((_snake(clase.__name__), nombre_campo))
        if enum:
            return list(enum)
    if modulo is not None:
        for singular, valores in _constantes_modulo(modulo).items():
            if nombre_campo == singular or nombre_campo.startswith(singular + "_"):
                return list(valores)
    return None
