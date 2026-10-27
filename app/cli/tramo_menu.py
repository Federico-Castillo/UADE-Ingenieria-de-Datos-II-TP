"""Menú de Tramo (Neo4j). Incluye las 2 "Consultas Avanzadas" pedidas
explícitamente por la consigna: ruta completa de un envío y red de
relaciones entre clientes, operadores y envíos."""
from datetime import date

from app.cli.io_utils import (
    leer_decimal_opcional,
    leer_entero,
    leer_no_vacio,
    leer_opcion,
    leer_opcional,
    pausar,
)
from app.core.exceptions import AppError
from app.domain.tramo import Tramo
from app.services.tramo_service import TramoService

_MEDIOS = {"terrestre", "maritimo", "aereo"}


def _leer_fecha_opcional(etiqueta: str) -> date | None:
    valor = input(f"{etiqueta} (opcional, YYYY-MM-DD): ").strip()
    if not valor:
        return None
    try:
        return date.fromisoformat(valor)
    except ValueError:
        print("  Fecha inválida, se deja vacía.")
        return None


def _leer_coordenada_opcional(etiqueta: str) -> float | None:
    valor = input(f"{etiqueta} (opcional): ").strip()
    if not valor:
        return None
    try:
        return float(valor)
    except ValueError:
        return None


def _registrar(service: TramoService) -> None:
    print("\n-- Registrar Tramo --")
    id_envio = leer_entero("ID de envío")
    medio_transporte = leer_opcion(f"Medio de transporte ({'/'.join(sorted(_MEDIOS))})", _MEDIOS)
    id_vehiculo = leer_entero("ID de vehículo")
    id_operador_logistico = leer_entero("ID de operador logístico")

    print("-- Origen --")
    origen_nombre = leer_no_vacio("Nombre del origen (ej. Puerto de Buenos Aires)")
    origen_pais = leer_opcional("País de origen")
    origen_lat = _leer_coordenada_opcional("Latitud de origen")
    origen_lon = _leer_coordenada_opcional("Longitud de origen")

    print("-- Destino --")
    destino_nombre = leer_no_vacio("Nombre del destino")
    destino_pais = leer_opcional("País de destino")
    destino_lat = _leer_coordenada_opcional("Latitud de destino")
    destino_lon = _leer_coordenada_opcional("Longitud de destino")

    fecha_salida = _leer_fecha_opcional("Fecha de salida")
    fecha_llegada = _leer_fecha_opcional("Fecha de llegada estimada")
    costo = leer_decimal_opcional("Costo del tramo")

    tramo = Tramo(
        id_envio=id_envio,
        medio_transporte=medio_transporte,
        id_vehiculo=id_vehiculo,
        id_operador_logistico=id_operador_logistico,
        origen_nombre=origen_nombre,
        destino_nombre=destino_nombre,
        origen_pais=origen_pais,
        origen_lat=origen_lat,
        origen_lon=origen_lon,
        destino_pais=destino_pais,
        destino_lat=destino_lat,
        destino_lon=destino_lon,
        fecha_salida=fecha_salida,
        fecha_llegada_estimada=fecha_llegada,
        costo=costo,
    )
    creado = service.registrar_tramo(tramo)
    print(f"Tramo creado con id {creado.id_tramo} (orden {creado.orden} del envío).")


def _ruta_completa(service: TramoService) -> None:
    print("\n-- Consulta Avanzada: Ruta Completa de un Envío --")
    id_envio = leer_entero("ID de envío")
    tramos = service.ruta_completa(id_envio)
    if not tramos:
        print("  Ese envío no tiene tramos registrados.")
    for t in tramos:
        print(
            f"  {t['orden']}) {t['origen']} -> {t['destino']} | {t['medio_transporte']} | "
            f"vehículo {t['vehiculo']} | salida {t['fecha_salida']} | llegada est. {t['fecha_llegada_estimada']}"
        )


def _red_relaciones(service: TramoService) -> None:
    print("\n-- Consulta Avanzada: Red de Relaciones Cliente-Operador-Envío --")
    filas = service.red_relaciones()
    if not filas:
        print("  Todavía no hay tramos cargados para armar la red.")
    for f in filas:
        print(f"  Cliente [{f['id_cliente']}] {f['cliente']}  <->  Operador [{f['id_operador_logistico']}] {f['operador']}")


_ACCIONES = {
    "1": ("Registrar tramo", _registrar),
    "2": ("Ruta completa de un envío", _ruta_completa),
    "3": ("Red de relaciones cliente-operador-envío", _red_relaciones),
}


def menu_tramo() -> None:
    service = TramoService()
    while True:
        print("\n=== Tramos y Rutas (Neo4j) ===")
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
