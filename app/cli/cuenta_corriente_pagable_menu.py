"""Menú de CuentaCorrientePagable: solo lectura, el saldo se gestiona
automáticamente desde FacturaRecibida/PagoEmitido."""
from app.cli.io_utils import leer_entero, leer_opcion, pausar
from app.core.exceptions import AppError
from app.domain.cuenta_corriente_pagable import CuentaCorrientePagable
from app.services.cuenta_corriente_pagable_service import CuentaCorrientePagableService


def _imprimir(c: CuentaCorrientePagable) -> None:
    titular = f"proveedor {c.id_proveedor}" if c.id_proveedor is not None else f"operador {c.id_operador_logistico}"
    print(f"  {titular} | saldo ${c.saldo:.2f} | actualizado {c.fecha_actualizacion or '-'}")


def _ver(service: CuentaCorrientePagableService) -> None:
    print("\n-- Cuenta Corriente Pagable --")
    tipo = leer_opcion("¿Proveedor u operador? (proveedor/operador)", {"proveedor", "operador"})
    if tipo == "proveedor":
        cuenta = service.obtener_por_proveedor(leer_entero("ID de proveedor"))
    else:
        cuenta = service.obtener_por_operador(leer_entero("ID de operador logístico"))
    _imprimir(cuenta)


def _listado(service: CuentaCorrientePagableService) -> None:
    print("\n-- Listado de Cuentas Corrientes Pagables --")
    cuentas = service.listar()
    if not cuentas:
        print("  No hay cuentas corrientes pagables todavía (se crean con la primera factura recibida).")
    for c in cuentas:
        _imprimir(c)


_ACCIONES = {
    "1": ("Ver cuenta corriente de proveedor/operador", _ver),
    "2": ("Listado general", _listado),
}


def menu_cuenta_corriente_pagable() -> None:
    service = CuentaCorrientePagableService()
    while True:
        print("\n=== Cuentas Corrientes Pagables (Proveedores/Operadores) ===")
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
