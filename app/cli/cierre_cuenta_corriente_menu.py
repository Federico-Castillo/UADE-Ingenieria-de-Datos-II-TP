"""Menú del proceso periódico "cierre mensual de cuentas corrientes". Pensado
para correrse una vez por mes (manualmente desde este menú, no hay scheduler
automático en el alcance del TP), pero es idempotente: reejecutar el cierre
de un período ya cerrado actualiza el snapshot en vez de duplicarlo."""
from app.cli.io_utils import leer_entero, leer_no_vacio, pausar
from app.core.exceptions import AppError
from app.domain.cierre_cuenta_corriente import CierreCuentaCorriente
from app.domain.cierre_cuenta_corriente_pagable import CierreCuentaCorrientePagable
from app.services.cierre_cuenta_corriente_service import CierreCuentaCorrienteService, periodo_actual


def _imprimir_cliente(c: CierreCuentaCorriente) -> None:
    print(f"  cliente {c.id_cliente} | período {c.periodo} | saldo al cierre ${c.saldo_al_cierre:.2f}")


def _imprimir_pagable(c: CierreCuentaCorrientePagable) -> None:
    titular = f"proveedor {c.id_proveedor}" if c.id_proveedor else f"operador {c.id_operador_logistico}"
    print(f"  {titular} | período {c.periodo} | saldo al cierre ${c.saldo_al_cierre:.2f}")


def _ejecutar_mes_actual(service: CierreCuentaCorrienteService) -> None:
    print(f"\n-- Ejecutar Cierre del Mes Actual ({periodo_actual()}) --")
    resultado = service.ejecutar_cierre_mensual()
    print(
        f"Cierre del período {resultado['periodo']} completo: "
        f"{resultado['clientes_cerrados']} cuenta(s) de clientes, "
        f"{resultado['pagables_cerrados']} cuenta(s) pagables."
    )


def _ejecutar_periodo(service: CierreCuentaCorrienteService) -> None:
    print("\n-- Ejecutar Cierre de un Período Específico --")
    periodo = leer_no_vacio("Período (YYYY-MM)")
    resultado = service.ejecutar_cierre_mensual(periodo)
    print(
        f"Cierre del período {resultado['periodo']} completo: "
        f"{resultado['clientes_cerrados']} cuenta(s) de clientes, "
        f"{resultado['pagables_cerrados']} cuenta(s) pagables."
    )


def _historial_cliente(service: CierreCuentaCorrienteService) -> None:
    print("\n-- Historial de Cierres de un Cliente --")
    id_cliente = leer_entero("ID de cliente")
    cierres = service.historial_cliente(id_cliente)
    if not cierres:
        print("  No hay cierres registrados para este cliente todavía.")
    for c in cierres:
        _imprimir_cliente(c)


def _historial_proveedor_u_operador(service: CierreCuentaCorrienteService) -> None:
    print("\n-- Historial de Cierres de un Proveedor/Operador --")
    tipo = leer_no_vacio("¿Proveedor u Operador? (p/o)").strip().lower()
    id_titular = leer_entero("ID")
    cierres = service.historial_proveedor(id_titular) if tipo == "p" else service.historial_operador(id_titular)
    if not cierres:
        print("  No hay cierres registrados todavía.")
    for c in cierres:
        _imprimir_pagable(c)


def _historial_periodo(service: CierreCuentaCorrienteService) -> None:
    print("\n-- Historial de Cierres de un Período --")
    periodo = leer_no_vacio("Período (YYYY-MM)")
    resultado = service.historial_periodo(periodo)
    if not resultado["clientes"] and not resultado["pagables"]:
        print("  No hay cierres registrados para este período todavía.")
    for c in resultado["clientes"]:
        _imprimir_cliente(c)
    for c in resultado["pagables"]:
        _imprimir_pagable(c)


_ACCIONES = {
    "1": ("Ejecutar cierre del mes actual", _ejecutar_mes_actual),
    "2": ("Ejecutar cierre de un período específico", _ejecutar_periodo),
    "3": ("Ver historial de cierres de un cliente", _historial_cliente),
    "4": ("Ver historial de cierres de un proveedor/operador", _historial_proveedor_u_operador),
    "5": ("Ver historial de cierres de un período (todas las cuentas)", _historial_periodo),
}


def menu_cierre_cuenta_corriente() -> None:
    service = CierreCuentaCorrienteService()
    while True:
        print("\n=== Cierre Mensual de Cuentas Corrientes (proceso periódico) ===")
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
