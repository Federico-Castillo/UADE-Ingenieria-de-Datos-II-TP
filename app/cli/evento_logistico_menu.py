"""Menú de EventoLogistico (MongoDB)."""
from app.cli.io_utils import leer_entero, leer_no_vacio, leer_opcional, limpiar_pantalla, pausar
from app.core.exceptions import AppError
from app.domain.evento_logistico import EventoLogistico
from app.services.evento_logistico_service import EventoLogisticoService


def _imprimir(e: EventoLogistico) -> None:
    ubicacion = f" @ {e.ubicacion}" if e.ubicacion else ""
    print(f"  [{e.id_evento}] envío {e.id_envio} | {e.tipo_evento}{ubicacion} | {e.fecha_hora}")


def _registrar(service: EventoLogisticoService) -> None:
    print("\n-- Registrar Evento Logístico --")
    descripcion = leer_opcional("Descripción") or ""
    evento = EventoLogistico(
        id_envio=leer_entero("ID de envío"),
        tipo_evento=leer_no_vacio("Tipo de evento (carga_iniciada/en_transito/aduana/retraso/descarga/entregado)"),
        descripcion=descripcion,
    )
    creado = service.registrar(evento)
    print(f"Evento registrado con id {creado.id_evento}.")


def _listado_por_envio(service: EventoLogisticoService) -> None:
    print("\n-- Historial de Eventos de un Envío --")
    id_envio = leer_entero("ID de envío")
    eventos = service.listar_por_envio(id_envio)
    if not eventos:
        print("  Ese envío no tiene eventos registrados.")
    for e in eventos:
        _imprimir(e)


def _listado(service: EventoLogisticoService) -> None:
    print("\n-- Últimos Eventos Logísticos --")
    eventos = service.listar()
    if not eventos:
        print("  No hay eventos para mostrar.")
    for e in eventos:
        _imprimir(e)


_ACCIONES = {
    "1": ("Registrar evento", _registrar),
    "2": ("Historial de un envío", _listado_por_envio),
    "3": ("Últimos eventos", _listado),
}


def menu_evento_logistico() -> None:
    service = EventoLogisticoService()
    while True:
        limpiar_pantalla()
        print("\n=== Eventos Logísticos (MongoDB) ===")
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
