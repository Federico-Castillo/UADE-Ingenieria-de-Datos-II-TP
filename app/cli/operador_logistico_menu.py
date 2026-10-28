"""Menú ABM de OperadorLogistico."""
from app.cli.io_utils import confirmar, leer_entero, leer_no_vacio, leer_opcion, leer_opcional, limpiar_pantalla, pausar
from app.core.exceptions import AppError
from app.domain.operador_logistico import OperadorLogistico
from app.services.operador_logistico_service import OperadorLogisticoService


def _imprimir(o: OperadorLogistico) -> None:
    print(
        f"  [{o.id_operador_logistico}] {o.razon_social} | CUIT {o.cuit} | "
        f"{o.email} | {o.telefono or '-'} | {o.estado}"
    )


def _alta(service: OperadorLogisticoService) -> None:
    print("\n-- Alta de Operador Logístico --")
    operador = OperadorLogistico(
        razon_social=leer_no_vacio("Razón social"),
        cuit=leer_no_vacio("CUIT (XX-XXXXXXXX-X)"),
        email=leer_no_vacio("Email"),
        telefono=leer_opcional("Teléfono"),
    )
    creado = service.dar_alta(operador)
    print(f"Operador logístico creado con id {creado.id_operador_logistico}.")


def _baja(service: OperadorLogisticoService) -> None:
    print("\n-- Baja de Operador Logístico --")
    id_operador = leer_entero("ID de operador logístico a dar de baja")
    operador = service.obtener_por_id(id_operador)
    _imprimir(operador)
    if confirmar("¿Confirmás la baja (lógica) de este operador logístico?"):
        service.dar_baja(id_operador)
        print("Operador logístico dado de baja.")
    else:
        print("Operación cancelada.")


def _modificacion(service: OperadorLogisticoService) -> None:
    print("\n-- Modificación de Operador Logístico --")
    id_operador = leer_entero("ID de operador logístico a modificar")
    operador = service.obtener_por_id(id_operador)
    _imprimir(operador)
    print("Dejá vacío para mantener el valor actual.")
    operador.razon_social = input(f"Razón social [{operador.razon_social}]: ").strip() or operador.razon_social
    operador.cuit = input(f"CUIT [{operador.cuit}]: ").strip() or operador.cuit
    operador.email = input(f"Email [{operador.email}]: ").strip() or operador.email
    operador.telefono = input(f"Teléfono [{operador.telefono or '-'}]: ").strip() or operador.telefono
    if confirmar("¿Querés cambiar el estado?"):
        operador.estado = leer_opcion(f"Estado [{operador.estado}] (activo/inactivo)", {"activo", "inactivo"})
    service.modificar(operador)
    print("Operador logístico modificado.")


def _listado(service: OperadorLogisticoService) -> None:
    print("\n-- Listado de Operadores Logísticos --")
    solo_activos = confirmar("¿Listar solo activos?")
    operadores = service.listar(solo_activos=solo_activos)
    if not operadores:
        print("  No hay operadores logísticos para mostrar.")
    for o in operadores:
        _imprimir(o)


def _busqueda(service: OperadorLogisticoService) -> None:
    print("\n-- Búsqueda de Operadores Logísticos --")
    texto = leer_no_vacio("Texto a buscar (razón social o CUIT)")
    operadores = service.buscar(texto)
    if not operadores:
        print("  No se encontraron operadores logísticos.")
    for o in operadores:
        _imprimir(o)


_ACCIONES = {
    "1": ("Alta", _alta),
    "2": ("Baja", _baja),
    "3": ("Modificación", _modificacion),
    "4": ("Listado", _listado),
    "5": ("Búsqueda", _busqueda),
}


def menu_operador_logistico() -> None:
    service = OperadorLogisticoService()
    while True:
        limpiar_pantalla()
        print("\n=== Gestión de Operadores Logísticos ===")
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
