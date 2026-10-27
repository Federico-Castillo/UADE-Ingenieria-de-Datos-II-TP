"""Menú ABM de Proveedor."""
from app.cli.io_utils import confirmar, leer_entero, leer_no_vacio, leer_opcion, leer_opcional, pausar
from app.core.exceptions import AppError
from app.domain.proveedor import Proveedor
from app.services.proveedor_service import ProveedorService


def _imprimir(p: Proveedor) -> None:
    print(
        f"  [{p.id_proveedor}] {p.razon_social} | CUIT {p.cuit} | {p.email} | "
        f"{p.telefono or '-'} | {p.pais or '-'} | {p.estado}"
    )


def _alta(service: ProveedorService) -> None:
    print("\n-- Alta de Proveedor --")
    proveedor = Proveedor(
        razon_social=leer_no_vacio("Razón social"),
        cuit=leer_no_vacio("CUIT (XX-XXXXXXXX-X)"),
        email=leer_no_vacio("Email"),
        telefono=leer_opcional("Teléfono"),
        direccion=leer_opcional("Dirección"),
        pais=leer_opcional("País"),
    )
    creado = service.dar_alta(proveedor)
    print(f"Proveedor creado con id {creado.id_proveedor}.")


def _baja(service: ProveedorService) -> None:
    print("\n-- Baja de Proveedor --")
    id_proveedor = leer_entero("ID de proveedor a dar de baja")
    proveedor = service.obtener_por_id(id_proveedor)
    _imprimir(proveedor)
    if confirmar("¿Confirmás la baja (lógica) de este proveedor?"):
        service.dar_baja(id_proveedor)
        print("Proveedor dado de baja.")
    else:
        print("Operación cancelada.")


def _modificacion(service: ProveedorService) -> None:
    print("\n-- Modificación de Proveedor --")
    id_proveedor = leer_entero("ID de proveedor a modificar")
    proveedor = service.obtener_por_id(id_proveedor)
    _imprimir(proveedor)
    print("Dejá vacío para mantener el valor actual.")
    proveedor.razon_social = input(f"Razón social [{proveedor.razon_social}]: ").strip() or proveedor.razon_social
    proveedor.cuit = input(f"CUIT [{proveedor.cuit}]: ").strip() or proveedor.cuit
    proveedor.email = input(f"Email [{proveedor.email}]: ").strip() or proveedor.email
    proveedor.telefono = input(f"Teléfono [{proveedor.telefono or '-'}]: ").strip() or proveedor.telefono
    proveedor.direccion = input(f"Dirección [{proveedor.direccion or '-'}]: ").strip() or proveedor.direccion
    proveedor.pais = input(f"País [{proveedor.pais or '-'}]: ").strip() or proveedor.pais
    if confirmar("¿Querés cambiar el estado?"):
        proveedor.estado = leer_opcion(f"Estado [{proveedor.estado}] (activo/inactivo)", {"activo", "inactivo"})
    service.modificar(proveedor)
    print("Proveedor modificado.")


def _listado(service: ProveedorService) -> None:
    print("\n-- Listado de Proveedores --")
    solo_activos = confirmar("¿Listar solo activos?")
    proveedores = service.listar(solo_activos=solo_activos)
    if not proveedores:
        print("  No hay proveedores para mostrar.")
    for p in proveedores:
        _imprimir(p)


def _busqueda(service: ProveedorService) -> None:
    print("\n-- Búsqueda de Proveedores --")
    texto = leer_no_vacio("Texto a buscar (razón social o CUIT)")
    proveedores = service.buscar(texto)
    if not proveedores:
        print("  No se encontraron proveedores.")
    for p in proveedores:
        _imprimir(p)


_ACCIONES = {
    "1": ("Alta", _alta),
    "2": ("Baja", _baja),
    "3": ("Modificación", _modificacion),
    "4": ("Listado", _listado),
    "5": ("Búsqueda", _busqueda),
}


def menu_proveedor() -> None:
    service = ProveedorService()
    while True:
        print("\n=== Gestión de Proveedores ===")
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
