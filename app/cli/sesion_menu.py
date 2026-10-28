"""Menú ABM de Sesión (Redis, con TTL)."""
from app.cli.io_utils import leer_entero, leer_no_vacio, limpiar_pantalla, pausar
from app.core.exceptions import AppError
from app.domain.sesion import Sesion
from app.services.sesion_service import SesionService


def _imprimir(s: Sesion) -> None:
    print(f"  [{s.id_sesion}] usuario {s.id_usuario} | inicio {s.fecha_inicio} | {s.estado}")


def _iniciar(service: SesionService) -> None:
    print("\n-- Iniciar Sesión --")
    id_usuario = leer_entero("ID de usuario")
    sesion = service.iniciar_sesion(id_usuario)
    print(f"Sesión iniciada: {sesion.id_sesion} (expira en 1 hora de inactividad).")


def _cerrar(service: SesionService) -> None:
    print("\n-- Cerrar Sesión --")
    id_sesion = leer_no_vacio("ID de sesión a cerrar")
    service.cerrar_sesion(id_sesion)
    print("Sesión cerrada.")


def _listar_de_usuario(service: SesionService) -> None:
    print("\n-- Sesiones activas de un usuario --")
    id_usuario = leer_entero("ID de usuario")
    sesiones = service.listar_activas_de_usuario(id_usuario)
    if not sesiones:
        print("  No tiene sesiones activas.")
    for s in sesiones:
        _imprimir(s)


def _listar_todas(service: SesionService) -> None:
    print("\n-- Todas las sesiones activas --")
    sesiones = service.listar_todas_activas()
    if not sesiones:
        print("  No hay sesiones activas.")
    for s in sesiones:
        _imprimir(s)


_ACCIONES = {
    "1": ("Iniciar sesión", _iniciar),
    "2": ("Cerrar sesión", _cerrar),
    "3": ("Sesiones activas de un usuario", _listar_de_usuario),
    "4": ("Todas las sesiones activas", _listar_todas),
}


def menu_sesion() -> None:
    service = SesionService()
    while True:
        limpiar_pantalla()
        print("\n=== Gestión de Sesiones ===")
        for key, (nombre, _) in _ACCIONES.items():
            print(f"{key}) {nombre}")
        print("0) Volver")
        opcion = input("Elegí una opción: ").strip()
        if opcion == "0":
            return
        accion = _ACCIONES.get(opcion)
        if accion is None:
            print("Opción inválida.")
            continue
        try:
            accion[1](service)
        except AppError as e:
            print(f"Error: {e}")
        pausar()
