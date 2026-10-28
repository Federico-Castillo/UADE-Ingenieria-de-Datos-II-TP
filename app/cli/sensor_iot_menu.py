"""Menú ABM de SensorIoT. Cubre también "ABM de sensores de un contenedor"
(listado filtrado por id_contenedor) del checklist de promoción."""
from datetime import date

from app.cli.io_utils import confirmar, leer_entero, leer_no_vacio, leer_opcion, leer_opcional, limpiar_pantalla, pausar
from app.core.exceptions import AppError
from app.domain.sensor_iot import SensorIoT
from app.services.sensor_iot_service import SensorIoTService


def _imprimir(s: SensorIoT) -> None:
    print(
        f"  [{s.id_sensor}] contenedor {s.id_contenedor} | {s.tipo} | "
        f"{s.fabricante or '-'} | instalado {s.fecha_instalacion or '-'} | {s.estado}"
    )


def _leer_fecha_opcional(etiqueta: str) -> date | None:
    valor = input(f"{etiqueta} (opcional, YYYY-MM-DD): ").strip()
    if not valor:
        return None
    try:
        return date.fromisoformat(valor)
    except ValueError:
        print("  Fecha inválida, se deja vacía.")
        return None


def _alta(service: SensorIoTService) -> None:
    print("\n-- Alta de Sensor IoT --")
    sensor = SensorIoT(
        id_contenedor=leer_entero("ID de contenedor asociado"),
        tipo=leer_no_vacio("Tipo (temperatura/humedad/vibracion/gps/bateria)"),
        fabricante=leer_opcional("Fabricante"),
        fecha_instalacion=_leer_fecha_opcional("Fecha de instalación"),
    )
    creado = service.dar_alta(sensor)
    print(f"Sensor creado con id {creado.id_sensor}.")


def _baja(service: SensorIoTService) -> None:
    print("\n-- Baja de Sensor IoT --")
    id_sensor = leer_entero("ID de sensor a eliminar")
    sensor = service.obtener_por_id(id_sensor)
    _imprimir(sensor)
    if confirmar("¿Confirmás eliminar este sensor?"):
        service.eliminar(id_sensor)
        print("Sensor eliminado.")
    else:
        print("Operación cancelada.")


def _modificacion(service: SensorIoTService) -> None:
    print("\n-- Modificación de Sensor IoT --")
    id_sensor = leer_entero("ID de sensor a modificar")
    sensor = service.obtener_por_id(id_sensor)
    _imprimir(sensor)
    print("Dejá vacío para mantener el valor actual.")
    sensor.tipo = input(f"Tipo [{sensor.tipo}]: ").strip() or sensor.tipo
    sensor.fabricante = input(f"Fabricante [{sensor.fabricante or '-'}]: ").strip() or sensor.fabricante
    if confirmar("¿Querés cambiar el estado?"):
        sensor.estado = leer_opcion(f"Estado [{sensor.estado}] (activo/inactivo)", {"activo", "inactivo"})
    service.modificar(sensor)
    print("Sensor modificado.")


def _listado(service: SensorIoTService) -> None:
    print("\n-- Listado de Sensores --")
    sensores = service.listar()
    if not sensores:
        print("  No hay sensores para mostrar.")
    for s in sensores:
        _imprimir(s)


def _listado_por_contenedor(service: SensorIoTService) -> None:
    print("\n-- Sensores de un Contenedor --")
    id_contenedor = leer_entero("ID de contenedor")
    sensores = service.listar_por_contenedor(id_contenedor)
    if not sensores:
        print("  Ese contenedor no tiene sensores asociados.")
    for s in sensores:
        _imprimir(s)


_ACCIONES = {
    "1": ("Alta", _alta),
    "2": ("Baja", _baja),
    "3": ("Modificación", _modificacion),
    "4": ("Listado", _listado),
    "5": ("Sensores de un contenedor", _listado_por_contenedor),
}


def menu_sensor_iot() -> None:
    service = SensorIoTService()
    while True:
        limpiar_pantalla()
        print("\n=== Gestión de Sensores IoT ===")
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
