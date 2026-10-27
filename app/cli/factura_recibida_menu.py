"""Menú de FacturaRecibida. El alta pide elegir si el emisor es un proveedor
o un operador logístico, consistente con la exclusión mutua del esquema."""
from app.cli.io_utils import leer_decimal, leer_entero, leer_opcion, pausar
from app.core.exceptions import AppError
from app.domain.factura_recibida import FacturaRecibida
from app.services.factura_recibida_service import FacturaRecibidaService


def _imprimir(f: FacturaRecibida) -> None:
    titular = f"proveedor {f.id_proveedor}" if f.id_proveedor is not None else f"operador {f.id_operador_logistico}"
    print(f"  [{f.id_factura_recibida}] {titular} | ${f.importe_total:.2f} | {f.estado} | {f.fecha_emision}")


def _alta(service: FacturaRecibidaService) -> None:
    print("\n-- Alta de Factura Recibida --")
    tipo = leer_opcion("¿Emisor? (proveedor/operador)", {"proveedor", "operador"})
    importe_total = leer_decimal("Importe total")
    if tipo == "proveedor":
        factura = FacturaRecibida(importe_total=importe_total, id_proveedor=leer_entero("ID de proveedor"))
    else:
        factura = FacturaRecibida(
            importe_total=importe_total, id_operador_logistico=leer_entero("ID de operador logístico")
        )
    creada = service.dar_alta(factura)
    print(
        f"Factura recibida creada con id {creada.id_factura_recibida}. "
        f"Se sumó ${creada.importe_total:.2f} a la cuenta corriente pagable correspondiente."
    )


def _listado(service: FacturaRecibidaService) -> None:
    print("\n-- Listado de Facturas Recibidas --")
    facturas = service.listar()
    if not facturas:
        print("  No hay facturas recibidas para mostrar.")
    for f in facturas:
        _imprimir(f)


def _listado_por_proveedor(service: FacturaRecibidaService) -> None:
    print("\n-- Facturas Recibidas de un Proveedor --")
    id_proveedor = leer_entero("ID de proveedor")
    facturas = service.listar_por_proveedor(id_proveedor)
    if not facturas:
        print("  Ese proveedor no tiene facturas recibidas.")
    for f in facturas:
        _imprimir(f)


def _listado_por_operador(service: FacturaRecibidaService) -> None:
    print("\n-- Facturas Recibidas de un Operador Logístico --")
    id_operador = leer_entero("ID de operador logístico")
    facturas = service.listar_por_operador(id_operador)
    if not facturas:
        print("  Ese operador logístico no tiene facturas recibidas.")
    for f in facturas:
        _imprimir(f)


_ACCIONES = {
    "1": ("Alta", _alta),
    "2": ("Listado", _listado),
    "3": ("Facturas de un proveedor", _listado_por_proveedor),
    "4": ("Facturas de un operador logístico", _listado_por_operador),
}


def menu_factura_recibida() -> None:
    service = FacturaRecibidaService()
    while True:
        print("\n=== Gestión de Facturas Recibidas ===")
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
