"""Registro de services: descubre app/services/*_service.py y crea cada
service la primera vez que se pide. Todos se construyen sin argumentos (igual
que en la CLI), así que no hace falta cablear nada a mano."""
import importlib
import inspect
import pkgutil

import app.services as _paquete

# No tienen sentido como "service que se prueba desde la UI".
_EXCLUIDOS: set[str] = set()


def _clase_service(modulo):
    for nombre, clase in inspect.getmembers(modulo, inspect.isclass):
        if nombre.endswith("Service") and clase.__module__ == modulo.__name__:
            return clase
    return None


def _descubrir() -> dict[str, type]:
    encontrados = {}
    for info in pkgutil.iter_modules(_paquete.__path__):
        if not info.name.endswith("_service") or info.name in _EXCLUIDOS:
            continue
        clase = _clase_service(importlib.import_module(f"app.services.{info.name}"))
        if clase is not None:
            encontrados[info.name.removesuffix("_service")] = clase
    return dict(sorted(encontrados.items()))


class RegistroServices:
    def __init__(self) -> None:
        self._clases = _descubrir()
        self._instancias: dict[str, object] = {}

    def nombres(self) -> list[str]:
        return list(self._clases)

    def obtener(self, nombre: str):
        if nombre not in self._instancias:
            self._instancias[nombre] = self._clases[nombre]()
        return self._instancias[nombre]


def etiqueta(nombre: str) -> str:
    return nombre.replace("_", " ").capitalize()
