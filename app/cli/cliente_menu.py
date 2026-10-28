"""Menú ABM de Cliente."""
import logging

from app.cli.io_utils import confirmar, leer_entero, leer_no_vacio, leer_opcion, leer_opcional, limpiar_pantalla, pausar
from app.core.exceptions import AppError
from app.domain.cliente import Cliente
from app.services.cliente_service import ClienteService

logger = logging.getLogger(__name__)


def _imprimir_cliente(c: Cliente) -> None:
    print(
        f"  [{c.id_cliente}] {c.razon_social} | CUIT {c.cuit} | {c.email} | "
        f"{c.telefono or '-'} | {c.pais or '-'} | {c.estado}"
    )


def _alta(service: ClienteService) -> None:
    print("\n-- Alta de Cliente --")
    cliente = Cliente(
        razon_social=leer_no_vacio("Razón social"),
        cuit=leer_no_vacio("CUIT (XX-XXXXXXXX-X)"),
        email=leer_no_vacio("Email"),
        telefono=leer_opcional("Teléfono"),
        direccion=leer_opcional("Dirección"),
        pais=leer_opcional("País"),
    )
    creado = service.dar_alta(cliente)
    print(f"Cliente creado con id {creado.id_cliente}.")


def _baja(service: ClienteService) -> None:
    print("\n-- Baja de Cliente --")
    id_cliente = leer_entero("ID de cliente a dar de baja")
    cliente = service.obtener_por_id(id_cliente)
    _imprimir_cliente(cliente)
    if confirmar("¿Confirmás la baja (lógica) de este cliente?"):
        service.dar_baja(id_cliente)
        print("Cliente dado de baja.")
    else:
        print("Operación cancelada.")


def _modificacion(service: ClienteService) -> None:
    print("\n-- Modificación de Cliente --")
    id_cliente = leer_entero("ID de cliente a modificar")
    cliente = service.obtener_por_id(id_cliente)
    _imprimir_cliente(cliente)
    print("Dejá vacío para mantener el valor actual.")
    cliente.razon_social = input(f"Razón social [{cliente.razon_social}]: ").strip() or cliente.razon_social
    cliente.cuit = input(f"CUIT [{cliente.cuit}]: ").strip() or cliente.cuit
    cliente.email = input(f"Email [{cliente.email}]: ").strip() or cliente.email
    cliente.telefono = input(f"Teléfono [{cliente.telefono or '-'}]: ").strip() or cliente.telefono
    cliente.direccion = input(f"Dirección [{cliente.direccion or '-'}]: ").strip() or cliente.direccion
    cliente.pais = input(f"País [{cliente.pais or '-'}]: ").strip() or cliente.pais
    cliente.estado = leer_opcion(f"Estado [{cliente.estado}] (activo/inactivo)", {"activo", "inactivo"}) \
        if confirmar("¿Querés cambiar el estado?") else cliente.estado
    service.modificar(cliente)
    print("Cliente modificado.")


def _listado(service: ClienteService) -> None:
    print("\n-- Listado de Clientes --")
    solo_activos = confirmar("¿Listar solo activos?")
    clientes = service.listar(solo_activos=solo_activos)
    if not clientes:
        print("  No hay clientes para mostrar.")
    for c in clientes:
        _imprimir_cliente(c)


def _busqueda(service: ClienteService) -> None:
    print("\n-- Búsqueda de Clientes --")
    texto = leer_no_vacio("Texto a buscar (razón social o CUIT)")
    clientes = service.buscar(texto)
    if not clientes:
        print("  No se encontraron clientes.")
    for c in clientes:
        _imprimir_cliente(c)


_ACCIONES = {
    "1": ("Alta", _alta),
    "2": ("Baja", _baja),
    "3": ("Modificación", _modificacion),
    "4": ("Listado", _listado),
    "5": ("Búsqueda", _busqueda),
}


def menu_cliente() -> None:
    service = ClienteService()
    while True:
        limpiar_pantalla()
        print("\n=== Gestión de Clientes ===")
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
