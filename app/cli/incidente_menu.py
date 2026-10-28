"""Menú de Incidente (MongoDB)."""
from app.cli.io_utils import confirmar, leer_entero, leer_no_vacio, leer_opcion, leer_opcional, limpiar_pantalla, pausar
from app.core.exceptions import AppError
from app.domain.incidente import Incidente
from app.services.incidente_service import IncidenteService

_SEVERIDADES = {"baja", "media", "alta", "critica"}
_ESTADOS = {"abierto", "en_revision", "cerrado"}


def _imprimir(i: Incidente) -> None:
    print(f"  [{i.id_incidente}] envío {i.id_envio} | {i.tipo} | severidad {i.severidad} | {i.estado} | {i.fecha}")


def _registrar(service: IncidenteService) -> None:
    print("\n-- Registrar Incidente --")
    incidente = Incidente(
        id_envio=leer_entero("ID de envío"),
        tipo=leer_no_vacio("Tipo de incidente (ej. demora_aduanera, rotura, robo)"),
        severidad=leer_opcion(f"Severidad ({'/'.join(sorted(_SEVERIDADES))})", _SEVERIDADES),
        descripcion=leer_opcional("Descripción") or "",
    )
    creado = service.registrar(incidente)
    print(f"Incidente registrado con id {creado.id_incidente}.")


def _cambiar_estado(service: IncidenteService) -> None:
    print("\n-- Cambiar Estado de Incidente --")
    id_incidente = leer_no_vacio("ID de incidente")
    nuevo_estado = leer_opcion(f"Nuevo estado ({'/'.join(sorted(_ESTADOS))})", _ESTADOS)
    service.cambiar_estado(id_incidente, nuevo_estado)
    print("Estado actualizado.")


def _listado_por_envio(service: IncidenteService) -> None:
    print("\n-- Incidentes de un Envío --")
    id_envio = leer_entero("ID de envío")
    incidentes = service.listar_por_envio(id_envio)
    if not incidentes:
        print("  Ese envío no tiene incidentes.")
    for i in incidentes:
        _imprimir(i)


def _listado(service: IncidenteService) -> None:
    print("\n-- Listado de Incidentes --")
    solo_abiertos = confirmar("¿Listar solo abiertos?")
    incidentes = service.listar(solo_abiertos=solo_abiertos)
    if not incidentes:
        print("  No hay incidentes para mostrar.")
    for i in incidentes:
        _imprimir(i)


_ACCIONES = {
    "1": ("Registrar incidente", _registrar),
    "2": ("Cambiar estado", _cambiar_estado),
    "3": ("Incidentes de un envío", _listado_por_envio),
    "4": ("Listado", _listado),
}


def menu_incidente() -> None:
    service = IncidenteService()
    while True:
        limpiar_pantalla()
        print("\n=== Incidentes (MongoDB) ===")
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
