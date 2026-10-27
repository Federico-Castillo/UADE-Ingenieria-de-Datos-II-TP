"""Menú ABM de Vehiculo."""
from app.cli.io_utils import confirmar, leer_entero, leer_no_vacio, leer_opcion, pausar
from app.core.exceptions import AppError
from app.domain.vehiculo import Vehiculo
from app.services.vehiculo_service import VehiculoService


def _imprimir(v: Vehiculo) -> None:
    print(f"  [{v.id_vehiculo}] {v.identificacion} | {v.tipo} | {v.empresa_operadora} | {v.estado}")


def _alta(service: VehiculoService) -> None:
    print("\n-- Alta de Vehículo --")
    vehiculo = Vehiculo(
        tipo=leer_no_vacio("Tipo (camion/barco/avion)"),
        identificacion=leer_no_vacio("Identificación (patente/matrícula)"),
        empresa_operadora=leer_no_vacio("Empresa operadora"),
    )
    creado = service.dar_alta(vehiculo)
    print(f"Vehículo creado con id {creado.id_vehiculo}.")


def _baja(service: VehiculoService) -> None:
    print("\n-- Baja de Vehículo --")
    id_vehiculo = leer_entero("ID de vehículo a eliminar")
    vehiculo = service.obtener_por_id(id_vehiculo)
    _imprimir(vehiculo)
    if confirmar("¿Confirmás eliminar este vehículo?"):
        service.eliminar(id_vehiculo)
        print("Vehículo eliminado.")
    else:
        print("Operación cancelada.")


def _modificacion(service: VehiculoService) -> None:
    print("\n-- Modificación de Vehículo --")
    id_vehiculo = leer_entero("ID de vehículo a modificar")
    vehiculo = service.obtener_por_id(id_vehiculo)
    _imprimir(vehiculo)
    print("Dejá vacío para mantener el valor actual.")
    vehiculo.tipo = input(f"Tipo [{vehiculo.tipo}]: ").strip() or vehiculo.tipo
    vehiculo.identificacion = input(f"Identificación [{vehiculo.identificacion}]: ").strip() or vehiculo.identificacion
    vehiculo.empresa_operadora = (
        input(f"Empresa operadora [{vehiculo.empresa_operadora}]: ").strip() or vehiculo.empresa_operadora
    )
    if confirmar("¿Querés cambiar el estado?"):
        vehiculo.estado = leer_opcion(
            f"Estado [{vehiculo.estado}] (disponible/en_viaje/en_mantenimiento)",
            {"disponible", "en_viaje", "en_mantenimiento"},
        )
    service.modificar(vehiculo)
    print("Vehículo modificado.")


def _listado(service: VehiculoService) -> None:
    print("\n-- Listado de Vehículos --")
    vehiculos = service.listar()
    if not vehiculos:
        print("  No hay vehículos para mostrar.")
    for v in vehiculos:
        _imprimir(v)


_ACCIONES = {
    "1": ("Alta", _alta),
    "2": ("Baja", _baja),
    "3": ("Modificación", _modificacion),
    "4": ("Listado", _listado),
}


def menu_vehiculo() -> None:
    service = VehiculoService()
    while True:
        print("\n=== Gestión de Vehículos ===")
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
