"""Menú de Factura. No tiene baja/modificación libre: es un documento
contable, y editar importe_total rompería la consistencia del saldo ya sumado
a la cuenta corriente en el alta."""
from app.cli.io_utils import leer_decimal, leer_entero, limpiar_pantalla, pausar
from app.core.exceptions import AppError
from app.domain.factura import Factura
from app.services.factura_service import FacturaService


def _imprimir(f: Factura) -> None:
    print(f"  [{f.id_factura}] cliente {f.id_cliente} | ${f.importe_total:.2f} | {f.estado} | {f.fecha_emision}")


def _alta(service: FacturaService) -> None:
    print("\n-- Alta de Factura --")
    factura = Factura(
        id_cliente=leer_entero("ID de cliente"),
        importe_total=leer_decimal("Importe total"),
    )
    creada = service.dar_alta(factura)
    print(f"Factura creada con id {creada.id_factura}. Se sumó ${creada.importe_total:.2f} a la cuenta corriente del cliente.")


def _listado(service: FacturaService) -> None:
    print("\n-- Listado de Facturas --")
    facturas = service.listar()
    if not facturas:
        print("  No hay facturas para mostrar.")
    for f in facturas:
        _imprimir(f)


def _listado_por_cliente(service: FacturaService) -> None:
    print("\n-- Facturas de un Cliente --")
    id_cliente = leer_entero("ID de cliente")
    facturas = service.listar_por_cliente(id_cliente)
    if not facturas:
        print("  Ese cliente no tiene facturas.")
    for f in facturas:
        _imprimir(f)


_ACCIONES = {
    "1": ("Alta", _alta),
    "2": ("Listado", _listado),
    "3": ("Facturas de un cliente", _listado_por_cliente),
}


def menu_factura() -> None:
    service = FacturaService()
    while True:
        limpiar_pantalla()
        print("\n=== Gestión de Facturas ===")
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
