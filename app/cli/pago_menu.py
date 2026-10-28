"""Menú de Pago. Alta únicamente (registro de pago): no tiene sentido
modificar/borrar un pago ya aplicado al saldo sin un proceso de reverso
explícito, que queda fuera de alcance de esta entrega."""
from app.cli.io_utils import leer_decimal, leer_entero, leer_no_vacio, limpiar_pantalla, pausar
from app.core.exceptions import AppError
from app.domain.pago import Pago
from app.services.pago_service import PagoService


def _imprimir(p: Pago) -> None:
    print(f"  [{p.id_pago}] factura {p.id_factura} | ${p.monto:.2f} | {p.medio_pago} | {p.fecha}")


def _registrar(service: PagoService) -> None:
    print("\n-- Registrar Pago --")
    pago = Pago(
        id_factura=leer_entero("ID de factura"),
        monto=leer_decimal("Monto"),
        medio_pago=leer_no_vacio("Medio de pago (efectivo/transferencia/tarjeta)"),
    )
    creado = service.registrar_pago(pago)
    print(f"Pago registrado con id {creado.id_pago}. Se descontó ${creado.monto:.2f} de la cuenta corriente del cliente.")


def _listado_por_factura(service: PagoService) -> None:
    print("\n-- Pagos de una Factura --")
    id_factura = leer_entero("ID de factura")
    pagos = service.listar_por_factura(id_factura)
    if not pagos:
        print("  Esa factura no tiene pagos registrados.")
    for p in pagos:
        _imprimir(p)


_ACCIONES = {
    "1": ("Registrar pago", _registrar),
    "2": ("Pagos de una factura", _listado_por_factura),
}


def menu_pago() -> None:
    service = PagoService()
    while True:
        limpiar_pantalla()
        print("\n=== Gestión de Pagos ===")
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
