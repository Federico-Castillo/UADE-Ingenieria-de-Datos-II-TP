"""Menú ABM de Rol."""
from app.cli.io_utils import confirmar, leer_entero, leer_no_vacio, limpiar_pantalla, pausar
from app.core.exceptions import AppError
from app.domain.rol import Rol
from app.services.rol_service import RolService


def _imprimir_rol(r: Rol) -> None:
    print(f"  [{r.id_rol}] {r.descripcion} | nivel de permisos: {r.nivel_permisos}")


def _alta(service: RolService) -> None:
    print("\n-- Alta de Rol --")
    rol = Rol(
        descripcion=leer_no_vacio("Descripción"),
        nivel_permisos=leer_entero("Nivel de permisos"),
    )
    creado = service.dar_alta(rol)
    print(f"Rol creado con id {creado.id_rol}.")


def _baja(service: RolService) -> None:
    print("\n-- Baja de Rol --")
    id_rol = leer_entero("ID de rol a eliminar")
    rol = service.obtener_por_id(id_rol)
    _imprimir_rol(rol)
    if confirmar("¿Confirmás eliminar este rol?"):
        service.eliminar(id_rol)
        print("Rol eliminado.")
    else:
        print("Operación cancelada.")


def _modificacion(service: RolService) -> None:
    print("\n-- Modificación de Rol --")
    id_rol = leer_entero("ID de rol a modificar")
    rol = service.obtener_por_id(id_rol)
    _imprimir_rol(rol)
    print("Dejá vacío para mantener el valor actual.")
    rol.descripcion = input(f"Descripción [{rol.descripcion}]: ").strip() or rol.descripcion
    nivel = input(f"Nivel de permisos [{rol.nivel_permisos}]: ").strip()
    rol.nivel_permisos = int(nivel) if nivel.isdigit() else rol.nivel_permisos
    service.modificar(rol)
    print("Rol modificado.")


def _listado(service: RolService) -> None:
    print("\n-- Listado de Roles --")
    roles = service.listar()
    if not roles:
        print("  No hay roles para mostrar.")
    for r in roles:
        _imprimir_rol(r)


_ACCIONES = {
    "1": ("Alta", _alta),
    "2": ("Baja", _baja),
    "3": ("Modificación", _modificacion),
    "4": ("Listado", _listado),
}


def menu_rol() -> None:
    service = RolService()
    while True:
        limpiar_pantalla()
        print("\n=== Gestión de Roles ===")
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
