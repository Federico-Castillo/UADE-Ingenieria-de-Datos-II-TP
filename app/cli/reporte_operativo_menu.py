"""Menú de Reportes Operativos y Analíticos: agregaciones de solo lectura
(no ABMs). Separado a propósito de "Gestión de Reportes" (menu_reporte.py),
que solo registra metadata del pedido — ver comentario en reporte_menu.py."""
from app.cli.io_utils import pausar
from app.core.exceptions import AppError
from app.services.reporte_operativo_service import ReporteOperativoService
from app.services.tramo_service import TramoService


def _envios_por_pais(service: ReporteOperativoService) -> None:
    print("\n-- Envíos por País --")
    filas = service.envios_por_pais()
    for f in filas:
        print(f"  {f['pais']}: {f['cantidad']}")


def _envios_por_estado(service: ReporteOperativoService) -> None:
    print("\n-- Envíos por Estado --")
    filas = service.envios_por_estado()
    for f in filas:
        print(f"  {f['estado']}: {f['cantidad']}")


def _envios_por_cliente(service: ReporteOperativoService) -> None:
    print("\n-- Envíos por Cliente --")
    filas = service.envios_por_cliente()
    for f in filas:
        print(f"  [{f['id_cliente']}] {f['razon_social']}: {f['cantidad']}")


def _envios_demorados(service: ReporteOperativoService) -> None:
    print("\n-- Envíos Demorados --")
    envios = service.envios_demorados()
    if not envios:
        print("  No hay envíos demorados.")
    for e in envios:
        print(f"  [{e.id_envio}] cliente {e.id_cliente} | {e.origen} -> {e.destino} | {e.fecha_creacion}")


def _incidentes_abiertos(service: ReporteOperativoService) -> None:
    print("\n-- Incidentes Abiertos --")
    incidentes = service.incidentes_abiertos()
    if not incidentes:
        print("  No hay incidentes abiertos.")
    for i in incidentes:
        print(f"  [{i.id_incidente}] envío {i.id_envio} | {i.tipo} | severidad {i.severidad} | {i.fecha}")


def _tiempos_envio_por_cliente(service: ReporteOperativoService) -> None:
    print("\n-- Tiempos de Envío por Cliente (mín/máx/promedio en hs) --")
    filas = service.tiempos_envio_por_cliente()
    if not filas:
        print("  No hay envíos con evento de entrega registrado todavía.")
    for f in filas:
        print(
            f"  [{f['id_cliente']}] {f['razon_social']} | {f['cantidad_envios']} envío(s) | "
            f"mín {f['horas_min']:.1f}hs | máx {f['horas_max']:.1f}hs | promedio {f['horas_promedio']:.1f}hs"
        )


def _tiempo_promedio_entrega(service: ReporteOperativoService) -> None:
    print("\n-- Tiempo Promedio de Entrega (global) --")
    resultado = service.tiempo_promedio_entrega()
    if resultado["cantidad_envios"] == 0:
        print("  No hay envíos con evento de entrega registrado todavía.")
    else:
        print(f"  {resultado['cantidad_envios']} envío(s) entregados | promedio {resultado['horas_promedio']:.1f}hs")


def _incidentes_promedio_por_pais(service: ReporteOperativoService) -> None:
    print("\n-- Promedio de Incidentes por País --")
    for f in service.incidentes_promedio_por_pais():
        print(
            f"  {f['grupo']}: {f['cantidad_incidentes']} incidente(s) / {f['cantidad_envios']} envío(s) "
            f"= {f['promedio_por_envio']:.2f} por envío"
        )


def _incidentes_promedio_por_estado(service: ReporteOperativoService) -> None:
    print("\n-- Promedio de Incidentes por Estado de Envío --")
    for f in service.incidentes_promedio_por_estado():
        print(
            f"  {f['grupo']}: {f['cantidad_incidentes']} incidente(s) / {f['cantidad_envios']} envío(s) "
            f"= {f['promedio_por_envio']:.2f} por envío"
        )


def _incidentes_promedio_por_cliente(service: ReporteOperativoService) -> None:
    print("\n-- Promedio de Incidentes por Cliente --")
    for f in service.incidentes_promedio_por_cliente():
        print(
            f"  [{f['grupo']}] {f['razon_social']}: {f['cantidad_incidentes']} incidente(s) / "
            f"{f['cantidad_envios']} envío(s) = {f['promedio_por_envio']:.2f} por envío"
        )


def _analisis_predictivo(service: ReporteOperativoService) -> None:
    print("\n-- Análisis Predictivo de Riesgos (atrasos) --")
    resultado = service.analisis_predictivo_riesgos()
    if resultado["cantidad_envios"] == 0:
        print("  No hay predicciones cargadas todavía (ver 'Predicciones de Riesgo (Mongo)').")
        return
    print(
        f"  {resultado['cantidad_envios']} envío(s) con predicción | "
        f"probabilidad de demora promedio {resultado['probabilidad_demora_promedio']:.2%}"
    )
    if resultado["envios_riesgo_alto"]:
        print("  Envíos en riesgo alto:")
        for r in resultado["envios_riesgo_alto"]:
            print(
                f"    envío {r['id_envio']} | prob. demora {r['probabilidad_demora']:.2%} | "
                f"riesgo climático {r['riesgo_climatico']:.2f} | riesgo operativo {r['riesgo_operativo']:.2f}"
            )
    else:
        print("  Ningún envío supera el umbral de riesgo alto.")


def _ranking_rutas_por_incidentes(service: ReporteOperativoService) -> None:
    print("\n-- Ranking de Rutas con Más Incidentes --")
    filas = service.ranking_rutas_por_incidentes()
    if not filas:
        print("  No hay rutas con incidentes registrados todavía.")
    for pos, f in enumerate(filas, start=1):
        print(
            f"  {pos}) {f['origen']} -> {f['destino']}: {f['cantidad_incidentes']} incidente(s) "
            f"en {f['cantidad_envios']} envío(s)"
        )


def _ranking_clientes_por_volumen(service: ReporteOperativoService) -> None:
    print("\n-- Ranking de Clientes por Volumen Transportado --")
    filas = service.ranking_clientes_por_volumen()
    if not filas:
        print("  No hay contenedores asignados a envíos todavía.")
    for pos, f in enumerate(filas, start=1):
        print(
            f"  {pos}) [{f['id_cliente']}] {f['razon_social']}: {f['volumen_total']:.2f} "
            f"({f['cantidad_contenedores']} contenedor(es))"
        )


def _costos_por_tipo_transporte(_: ReporteOperativoService) -> None:
    print("\n-- Costos por Tipo de Transporte --")
    filas = TramoService().costos_por_medio_transporte()
    if not filas:
        print("  No hay tramos con costo cargado todavía (campo opcional al registrar un Tramo).")
    for f in filas:
        print(
            f"  {f['medio_transporte']}: {f['cantidad_tramos']} tramo(s) | "
            f"costo promedio ${f['costo_promedio']:.2f} | costo total ${f['costo_total']:.2f}"
        )


_ACCIONES = {
    "1": ("Envíos por país", _envios_por_pais),
    "2": ("Envíos por estado", _envios_por_estado),
    "3": ("Envíos por cliente", _envios_por_cliente),
    "4": ("Envíos demorados", _envios_demorados),
    "5": ("Incidentes abiertos", _incidentes_abiertos),
    "6": ("Tiempos de envío por cliente (mín/máx/promedio)", _tiempos_envio_por_cliente),
    "7": ("Tiempo promedio de entrega (global)", _tiempo_promedio_entrega),
    "8": ("Incidentes promedio por país", _incidentes_promedio_por_pais),
    "9": ("Incidentes promedio por estado", _incidentes_promedio_por_estado),
    "10": ("Incidentes promedio por cliente", _incidentes_promedio_por_cliente),
    "11": ("Análisis predictivo de riesgos (atrasos)", _analisis_predictivo),
    "12": ("Costos por tipo de transporte", _costos_por_tipo_transporte),
    "13": ("Ranking: rutas con más incidentes", _ranking_rutas_por_incidentes),
    "14": ("Ranking: clientes por volumen transportado", _ranking_clientes_por_volumen),
}


def menu_reporte_operativo() -> None:
    service = ReporteOperativoService()
    while True:
        print("\n=== Reportes Operativos y Analíticos ===")
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
