"""Menú del proceso periódico "detección de sensores inactivos"."""
from app.cli.io_utils import confirmar, leer_decimal, limpiar_pantalla, pausar
from app.core.exceptions import AppError
from app.domain.sensor_iot import SensorIoT
from app.services.sensor_inactivo_service import UMBRAL_HORAS_DEFAULT, SensorInactivoService


def _imprimir(s: SensorIoT) -> None:
    print(f"  sensor {s.id_sensor} ({s.tipo}) | contenedor {s.id_contenedor} | estado {s.estado}")


def _leer_umbral() -> float:
    if confirmar(f"¿Usar el umbral por defecto ({UMBRAL_HORAS_DEFAULT:.0f}hs)?"):
        return UMBRAL_HORAS_DEFAULT
    return leer_decimal("Umbral en horas")


def _detectar(service: SensorInactivoService) -> None:
    print("\n-- Detectar Sensores Inactivos (sin marcar) --")
    umbral = _leer_umbral()
    detectados = service.detectar(umbral)
    if not detectados:
        print(f"  No hay sensores activos sin lecturas en las últimas {umbral:.0f}hs.")
    for s in detectados:
        _imprimir(s)


def _marcar(service: SensorInactivoService) -> None:
    print("\n-- Detectar y Marcar Sensores Inactivos --")
    umbral = _leer_umbral()
    marcados = service.marcar_inactivos(umbral)
    if not marcados:
        print(f"  No hay sensores activos sin lecturas en las últimas {umbral:.0f}hs.")
    else:
        print(f"  {len(marcados)} sensor(es) marcados como 'inactivo' (se generó una alerta por cada uno):")
    for s in marcados:
        _imprimir(s)


_ACCIONES = {
    "1": ("Detectar sensores inactivos (sin marcar)", _detectar),
    "2": ("Detectar y marcar como inactivos + generar alertas", _marcar),
}


def menu_sensor_inactivo() -> None:
    service = SensorInactivoService()
    while True:
        limpiar_pantalla()
        print("\n=== Detección de Sensores Inactivos (proceso periódico) ===")
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
