"""Menú de PagoEmitido (pagos a proveedores/operadores logísticos)."""
from app.cli.io_utils import leer_decimal, leer_entero, leer_no_vacio, pausar
from app.core.exceptions import AppError
from app.domain.pago_emitido import PagoEmitido
from app.services.pago_emitido_service import PagoEmitidoService


def _imprimir(p: PagoEmitido) -> None:
    print(f"  [{p.id_pago_emitido}] factura {p.id_factura_recibida} | ${p.monto:.2f} | {p.medio_pago} | {p.fecha}")


def _registrar(service: PagoEmitidoService) -> None:
    print("\n-- Registrar Pago Emitido --")
    pago = PagoEmitido(
        id_factura_recibida=leer_entero("ID de factura recibida"),
        monto=leer_decimal("Monto"),
        medio_pago=leer_no_vacio("Medio de pago (efectivo/transferencia/tarjeta)"),
    )
    creado = service.registrar_pago(pago)
    print(
        f"Pago registrado con id {creado.id_pago_emitido}. "
        f"Se descontó ${creado.monto:.2f} de la cuenta corriente pagable correspondiente."
    )


def _listado_por_factura(service: PagoEmitidoService) -> None:
    print("\n-- Pagos de una Factura Recibida --")
    id_factura = leer_entero("ID de factura recibida")
    pagos = service.listar_por_factura(id_factura)
    if not pagos:
        print("  Esa factura no tiene pagos registrados.")
    for p in pagos:
        _imprimir(p)


_ACCIONES = {
    "1": ("Registrar pago", _registrar),
    "2": ("Pagos de una factura recibida", _listado_por_factura),
}


def menu_pago_emitido() -> None:
    service = PagoEmitidoService()
    while True:
        print("\n=== Gestión de Pagos Emitidos ===")
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
