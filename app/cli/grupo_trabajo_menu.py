"""Menú de GrupoTrabajo (MongoDB)."""
from app.cli.io_utils import leer_entero, leer_no_vacio, pausar
from app.core.exceptions import AppError
from app.domain.grupo_trabajo import GrupoTrabajo
from app.services.grupo_trabajo_service import GrupoTrabajoService


def _imprimir(g: GrupoTrabajo) -> None:
    print(f"  [{g.id_grupo}] {g.nombre} | integrantes: {g.integrantes}")


def _leer_integrantes() -> list[int]:
    raw = input("IDs de usuario integrantes, separados por coma (opcional): ").strip()
    if not raw:
        return []
    return [int(x) for x in raw.split(",") if x.strip().isdigit()]


def _crear(service: GrupoTrabajoService) -> None:
    print("\n-- Crear Grupo de Trabajo --")
    grupo = GrupoTrabajo(nombre=leer_no_vacio("Nombre del grupo"), integrantes=_leer_integrantes())
    creado = service.crear(grupo)
    print(f"Grupo creado con id {creado.id_grupo}.")


def _agregar_integrante(service: GrupoTrabajoService) -> None:
    print("\n-- Agregar Integrante --")
    id_grupo = leer_no_vacio("ID de grupo")
    id_usuario = leer_entero("ID de usuario a agregar")
    service.agregar_integrante(id_grupo, id_usuario)
    print("Integrante agregado.")


def _quitar_integrante(service: GrupoTrabajoService) -> None:
    print("\n-- Quitar Integrante --")
    id_grupo = leer_no_vacio("ID de grupo")
    id_usuario = leer_entero("ID de usuario a quitar")
    service.quitar_integrante(id_grupo, id_usuario)
    print("Integrante quitado.")


def _listado(service: GrupoTrabajoService) -> None:
    print("\n-- Listado de Grupos de Trabajo --")
    grupos = service.listar()
    if not grupos:
        print("  No hay grupos para mostrar.")
    for g in grupos:
        _imprimir(g)


_ACCIONES = {
    "1": ("Crear grupo", _crear),
    "2": ("Agregar integrante", _agregar_integrante),
    "3": ("Quitar integrante", _quitar_integrante),
    "4": ("Listado", _listado),
}


def menu_grupo_trabajo() -> None:
    service = GrupoTrabajoService()
    while True:
        print("\n=== Grupos de Trabajo (MongoDB) ===")
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
