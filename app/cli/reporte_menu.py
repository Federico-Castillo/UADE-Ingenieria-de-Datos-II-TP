"""Menú de Reporte. 'Generar' es el alta (simula la generación — el contenido
real del reporte, cuando se implementen los reportes operativos/analíticos
pedidos por la consigna, se calculará aparte; esta entidad solo registra el
pedido/metadata)."""
from app.cli.io_utils import confirmar, leer_entero, leer_no_vacio, leer_opcion, pausar
from app.core.exceptions import AppError
from app.domain.reporte import Reporte
from app.services.reporte_service import ReporteService

_FORMATOS = {"pdf", "csv", "xlsx"}


def _imprimir(r: Reporte) -> None:
    print(f"  [{r.id_reporte}] usuario {r.id_usuario} | {r.tipo} | {r.formato} | {r.estado} | {r.fecha_generacion}")


def _generar(service: ReporteService) -> None:
    print("\n-- Generar Reporte --")
    reporte = Reporte(
        id_usuario=leer_entero("ID de usuario solicitante"),
        tipo=leer_no_vacio("Tipo de reporte (ej. envios_por_cliente, incidentes_por_pais)"),
        formato=leer_opcion(f"Formato ({'/'.join(sorted(_FORMATOS))})", _FORMATOS),
    )
    creado = service.generar(reporte)
    print(f"Reporte generado con id {creado.id_reporte}.")


def _baja(service: ReporteService) -> None:
    print("\n-- Eliminar Reporte --")
    id_reporte = leer_entero("ID de reporte a eliminar")
    reporte = service.obtener_por_id(id_reporte)
    _imprimir(reporte)
    if confirmar("¿Confirmás eliminar este reporte?"):
        service.eliminar(id_reporte)
        print("Reporte eliminado.")
    else:
        print("Operación cancelada.")


def _listado(service: ReporteService) -> None:
    print("\n-- Listado de Reportes --")
    reportes = service.listar()
    if not reportes:
        print("  No hay reportes para mostrar.")
    for r in reportes:
        _imprimir(r)


def _listado_por_usuario(service: ReporteService) -> None:
    print("\n-- Reportes de un Usuario --")
    id_usuario = leer_entero("ID de usuario")
    reportes = service.listar_por_usuario(id_usuario)
    if not reportes:
        print("  Ese usuario no generó reportes.")
    for r in reportes:
        _imprimir(r)


_ACCIONES = {
    "1": ("Generar", _generar),
    "2": ("Eliminar", _baja),
    "3": ("Listado", _listado),
    "4": ("Reportes de un usuario", _listado_por_usuario),
}


def menu_reporte() -> None:
    service = ReporteService()
    while True:
        print("\n=== Gestión de Reportes ===")
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
