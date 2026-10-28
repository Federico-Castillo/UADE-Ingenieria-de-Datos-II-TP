"""Menú de CuentaCorriente: solo lectura, el saldo se gestiona automáticamente
desde Factura/Pago (ver cuenta_corriente_repository.py)."""
from app.cli.io_utils import leer_entero, limpiar_pantalla, pausar
from app.core.exceptions import AppError
from app.domain.cuenta_corriente import CuentaCorriente
from app.services.cuenta_corriente_service import CuentaCorrienteService


def _imprimir(c: CuentaCorriente) -> None:
    print(f"  cliente {c.id_cliente} | saldo ${c.saldo:.2f} | actualizado {c.fecha_actualizacion or '-'}")


def _ver_de_cliente(service: CuentaCorrienteService) -> None:
    print("\n-- Cuenta Corriente de un Cliente --")
    id_cliente = leer_entero("ID de cliente")
    cuenta = service.obtener_por_cliente(id_cliente)
    _imprimir(cuenta)


def _listado(service: CuentaCorrienteService) -> None:
    print("\n-- Listado de Cuentas Corrientes --")
    cuentas = service.listar()
    if not cuentas:
        print("  No hay cuentas corrientes todavía (se crean con la primera factura).")
    for c in cuentas:
        _imprimir(c)


_ACCIONES = {
    "1": ("Ver cuenta corriente de un cliente", _ver_de_cliente),
    "2": ("Listado general", _listado),
}


def menu_cuenta_corriente() -> None:
    service = CuentaCorrienteService()
    while True:
        limpiar_pantalla()
        print("\n=== Cuentas Corrientes (Clientes) ===")
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
