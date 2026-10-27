"""Menú ABM de Envio."""
from app.cli.io_utils import confirmar, leer_entero, leer_no_vacio, leer_opcion, pausar
from app.core.exceptions import AppError
from app.domain.envio import Envio
from app.services.envio_service import EnvioService

_PRIORIDADES = {"baja", "normal", "alta", "urgente"}
_ESTADOS = {"pendiente", "en_transito", "entregado", "demorado", "cancelado"}


def _imprimir(e: Envio) -> None:
    print(
        f"  [{e.id_envio}] cliente {e.id_cliente} | {e.origen} -> {e.destino} | "
        f"{e.estado} | prioridad {e.prioridad} | {e.fecha_creacion}"
    )


def _alta(service: EnvioService) -> None:
    print("\n-- Alta de Envío --")
    envio = Envio(
        id_cliente=leer_entero("ID de cliente"),
        origen=leer_no_vacio("Origen"),
        destino=leer_no_vacio("Destino"),
        estado=leer_opcion(f"Estado ({'/'.join(sorted(_ESTADOS))})", _ESTADOS),
        prioridad=leer_opcion(f"Prioridad ({'/'.join(sorted(_PRIORIDADES))})", _PRIORIDADES),
    )
    creado = service.dar_alta(envio)
    print(f"Envío creado con id {creado.id_envio}.")


def _baja(service: EnvioService) -> None:
    print("\n-- Baja de Envío --")
    id_envio = leer_entero("ID de envío a eliminar")
    envio = service.obtener_por_id(id_envio)
    _imprimir(envio)
    if confirmar("¿Confirmás eliminar este envío?"):
        service.eliminar(id_envio)
        print("Envío eliminado.")
    else:
        print("Operación cancelada.")


def _modificacion(service: EnvioService) -> None:
    print("\n-- Modificación de Envío --")
    id_envio = leer_entero("ID de envío a modificar")
    envio = service.obtener_por_id(id_envio)
    _imprimir(envio)
    print("Dejá vacío para mantener el valor actual.")
    envio.origen = input(f"Origen [{envio.origen}]: ").strip() or envio.origen
    envio.destino = input(f"Destino [{envio.destino}]: ").strip() or envio.destino
    if confirmar(f"¿Cambiar estado (actual: {envio.estado})?"):
        envio.estado = leer_opcion(f"Estado ({'/'.join(sorted(_ESTADOS))})", _ESTADOS)
    if confirmar(f"¿Cambiar prioridad (actual: {envio.prioridad})?"):
        envio.prioridad = leer_opcion(f"Prioridad ({'/'.join(sorted(_PRIORIDADES))})", _PRIORIDADES)
    service.modificar(envio)
    print("Envío modificado.")


def _listado(service: EnvioService) -> None:
    print("\n-- Listado de Envíos --")
    envios = service.listar()
    if not envios:
        print("  No hay envíos para mostrar.")
    for e in envios:
        _imprimir(e)


def _listado_por_cliente(service: EnvioService) -> None:
    print("\n-- Envíos de un Cliente --")
    id_cliente = leer_entero("ID de cliente")
    envios = service.listar_por_cliente(id_cliente)
    if not envios:
        print("  Ese cliente no tiene envíos.")
    for e in envios:
        _imprimir(e)


_ACCIONES = {
    "1": ("Alta", _alta),
    "2": ("Baja", _baja),
    "3": ("Modificación", _modificacion),
    "4": ("Listado", _listado),
    "5": ("Envíos de un cliente", _listado_por_cliente),
}


def menu_envio() -> None:
    service = EnvioService()
    while True:
        print("\n=== Gestión de Envíos ===")
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
