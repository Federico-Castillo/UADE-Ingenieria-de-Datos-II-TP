"""Menú de LecturaSensor (Cassandra). Cubre "Monitoreo IoT": registro
continuo de lecturas, consulta histórica, el disparo automático de
Incidente (Mongo) + Alerta (Redis) cuando una lectura viola una Regla activa
del tipo de sensor correspondiente, la reconstrucción del recorrido de un
contenedor (combinando todos sus sensores), y la visualización geográfica
del recorrido en un mapa HTML."""
from datetime import datetime

from app.cli.io_utils import leer_entero, pausar
from app.core.exceptions import AppError
from app.domain.lectura_sensor import LecturaSensor
from app.services.lectura_sensor_service import LecturaSensorService
from app.services.mapa_service import MapaService


def _leer_decimal_opcional(etiqueta: str) -> float | None:
    valor = input(f"{etiqueta} (opcional): ").strip().replace(",", ".")
    if not valor:
        return None
    try:
        return float(valor)
    except ValueError:
        print("  Valor inválido, se deja vacío.")
        return None


def _leer_datetime(etiqueta: str) -> datetime:
    while True:
        valor = input(f"{etiqueta} (YYYY-MM-DD HH:MM): ").strip()
        try:
            return datetime.strptime(valor, "%Y-%m-%d %H:%M")
        except ValueError:
            print("  Formato inválido.")


def _imprimir(l: LecturaSensor) -> None:
    print(
        f"  [{l.id_lectura}] sensor {l.id_sensor} | {l.fecha_hora} | temp {l.temperatura} | "
        f"hum {l.humedad} | vib {l.vibracion} | bat {l.nivel_bateria} | gps ({l.gps_lat}, {l.gps_lon})"
    )


def _registrar(service: LecturaSensorService) -> None:
    print("\n-- Registrar Lectura de Sensor --")
    lectura = LecturaSensor(
        id_sensor=leer_entero("ID de sensor"),
        temperatura=_leer_decimal_opcional("Temperatura"),
        humedad=_leer_decimal_opcional("Humedad"),
        vibracion=_leer_decimal_opcional("Vibración"),
        gps_lat=_leer_decimal_opcional("Latitud GPS"),
        gps_lon=_leer_decimal_opcional("Longitud GPS"),
        nivel_bateria=_leer_decimal_opcional("Nivel de batería"),
    )
    creada = service.registrar_lectura(lectura)
    print(f"Lectura registrada con id {creada.id_lectura} a las {creada.fecha_hora}.")
    print("(Si violó alguna regla activa, ya se generó el incidente/alerta correspondiente.)")


def _listado_por_sensor(service: LecturaSensorService) -> None:
    print("\n-- Últimas Lecturas de un Sensor --")
    id_sensor = leer_entero("ID de sensor")
    lecturas = service.listar_por_sensor(id_sensor)
    if not lecturas:
        print("  Ese sensor no tiene lecturas.")
    for l in lecturas:
        _imprimir(l)


def _listado_por_rango(service: LecturaSensorService) -> None:
    print("\n-- Lecturas de un Sensor por Rango de Fechas --")
    id_sensor = leer_entero("ID de sensor")
    desde = _leer_datetime("Desde")
    hasta = _leer_datetime("Hasta")
    lecturas = service.listar_por_rango(id_sensor, desde, hasta)
    if not lecturas:
        print("  No hay lecturas en ese rango.")
    for l in lecturas:
        _imprimir(l)


def _ultima(service: LecturaSensorService) -> None:
    print("\n-- Última Lectura de un Sensor --")
    id_sensor = leer_entero("ID de sensor")
    lectura = service.ultima_por_sensor(id_sensor)
    if lectura is None:
        print("  Ese sensor no tiene lecturas.")
    else:
        _imprimir(lectura)


def _recorrido_contenedor(service: LecturaSensorService) -> None:
    print("\n-- Reconstrucción del Recorrido de un Contenedor --")
    id_contenedor = leer_entero("ID de contenedor")
    lecturas = service.listar_por_contenedor(id_contenedor)
    if not lecturas:
        print("  Ese contenedor no tiene lecturas todavía.")
    for l in lecturas:
        _imprimir(l)


def _generar_mapa(_: LecturaSensorService) -> None:
    print("\n-- Generar Mapa GPS de un Contenedor --")
    id_contenedor = leer_entero("ID de contenedor")
    ruta = MapaService().generar_mapa_contenedor(id_contenedor)
    print(f"Mapa generado: {ruta}")
    print("Abrilo con el navegador para verlo.")


_ACCIONES = {
    "1": ("Registrar lectura", _registrar),
    "2": ("Últimas lecturas de un sensor", _listado_por_sensor),
    "3": ("Lecturas por rango de fechas", _listado_por_rango),
    "4": ("Última lectura de un sensor", _ultima),
    "5": ("Reconstrucción del recorrido de un contenedor", _recorrido_contenedor),
    "6": ("Generar mapa GPS de un contenedor (HTML)", _generar_mapa),
}


def menu_lectura_sensor() -> None:
    service = LecturaSensorService()
    while True:
        print("\n=== Monitoreo IoT: Lecturas de Sensor (Cassandra) ===")
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
