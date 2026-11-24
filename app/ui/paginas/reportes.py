"""Reportes operativos y analíticos con gráficos, en 5 pestañas."""
import logging

from nicegui import ui

from app.ui.comun import encabezado, llamar, reg, tabla_simple

logger = logging.getLogger(__name__)


def _barras(titulo: str, filas: list[dict], x: str, y: str) -> dict:
    return {
        "title": {"text": titulo},
        "tooltip": {},
        "xAxis": {"type": "category", "data": [str(f[x]) for f in filas]},
        "yAxis": {"type": "value"},
        "series": [{"type": "bar", "data": [f[y] for f in filas]}],
    }


def _lineas(titulo: str, filas: list[dict], x: str, series: dict[str, str]) -> dict:
    return {
        "title": {"text": titulo},
        "tooltip": {"trigger": "axis"},
        "legend": {"top": 24},
        "xAxis": {"type": "category", "data": [str(f[x]) for f in filas]},
        "yAxis": {"type": "value"},
        "series": [{"name": nombre, "type": "line", "data": [f[campo] for f in filas]} for nombre, campo in series.items()],
    }


def _grafico(opciones: dict) -> None:
    ui.echart(opciones).classes("w-full max-w-3xl h-72")


@ui.page("/reportes")
async def pagina_reportes() -> None:
    encabezado("Reportes operativos y analíticos")
    try:
        servicio = reg().obtener("reporte_operativo")
        servicio_tramo = reg().obtener("tramo")
        servicio_ml = reg().obtener("prediccion_ml")
    except Exception as ex:
        logger.exception("No se pudieron crear los services de reportes")
        ui.notify(f"No se pudo conectar a los motores: {ex}", type="negative", multi_line=True)
        return

    nombres = ["Envíos", "Incidentes", "Desempeño histórico", "Riesgo de atrasos", "Transporte y clientes"]
    with ui.row().classes("p-4 items-center gap-4"):
        ui.button("Actualizar", icon="refresh", on_click=lambda: cargar(tabs.value))
        boton_ml = ui.button("Recalcular predicciones (ML)", icon="psychology", color="secondary")
    with ui.tabs().classes("w-full") as tabs:
        for n in nombres:
            ui.tab(n)
    paneles = {}
    with ui.tab_panels(tabs, value=nombres[0]).classes("w-full"):
        for n in nombres:
            with ui.tab_panel(n):
                paneles[n] = ui.column().classes("w-full gap-2")

    async def _datos(*llamadas):
        """Ejecuta varios métodos; devuelve sus resultados o None si alguno falló."""
        resultados = []
        for f, *args in llamadas:
            ok, r = await llamar(f, *args)
            if not ok:
                return None
            resultados.append(r)
        return resultados

    async def cargar_envios() -> None:
        d = await _datos((servicio.envios_por_pais,), (servicio.envios_por_estado,), (servicio.tiempo_promedio_entrega,),
                         (servicio.envios_por_cliente,), (servicio.tiempos_envio_por_cliente,), (servicio.envios_demorados,))
        if d is None:
            return
        por_pais, por_estado, promedio, por_cliente, tiempos, demorados = d
        with paneles["Envíos"]:
            with ui.row().classes("gap-6"):
                _grafico(_barras("Envíos por país", por_pais, "pais", "cantidad"))
                _grafico(_barras("Envíos por estado", por_estado, "estado", "cantidad"))
            horas = promedio["horas_promedio"]
            texto_horas = "sin datos" if horas is None else f"{horas:.1f} h"
            ui.label(f"Tiempo promedio de entrega: {texto_horas} ({promedio['cantidad_envios']} envíos entregados)").classes("text-lg")
            tabla_simple("Envíos por cliente", por_cliente)
            tabla_simple("Tiempos de entrega por cliente (horas)", tiempos)
            tabla_simple("Envíos demorados", demorados)

    async def cargar_incidentes() -> None:
        d = await _datos((servicio.incidentes_promedio_por_pais,), (servicio.incidentes_promedio_por_estado,),
                         (servicio.incidentes_promedio_por_cliente,), (servicio.ranking_rutas_por_incidentes, 10),
                         (servicio.incidentes_abiertos,))
        if d is None:
            return
        por_pais, por_estado, por_cliente, rutas, abiertos = d
        with paneles["Incidentes"]:
            with ui.row().classes("gap-6"):
                _grafico(_barras("Incidentes por envío, por país", por_pais, "grupo", "promedio_por_envio"))
                _grafico(_barras("Incidentes por envío, por estado", por_estado, "grupo", "promedio_por_envio"))
            tabla_simple("Incidentes promedio por cliente", por_cliente)
            tabla_simple("Ranking de rutas con más incidentes", rutas)
            tabla_simple("Incidentes abiertos", abiertos)

    async def cargar_desempeno() -> None:
        d = await _datos((servicio.desempeno_historico_mensual,))
        if d is None:
            return
        (historico,) = d
        with paneles["Desempeño histórico"]:
            if historico:
                _grafico(_lineas("Evolución mensual", historico, "periodo", {
                    "Envíos": "cantidad_envios", "Demorados": "cantidad_demorados",
                    "Incidentes": "cantidad_incidentes", "Entregados": "cantidad_entregados"}))
                _grafico(_lineas("% de envíos demorados", historico, "periodo", {"% demorados": "porcentaje_demorados"}))
            tabla_simple("Detalle mensual", historico)

    async def cargar_riesgo() -> None:
        d = await _datos((servicio.analisis_predictivo_riesgos,))
        if d is None:
            return
        (analisis,) = d
        with paneles["Riesgo de atrasos"]:
            ui.label(f"Envíos analizados: {analisis['cantidad_envios']} | probabilidad de demora promedio: "
                     f"{analisis['probabilidad_demora_promedio']:.0%}").classes("text-lg")
            altos = analisis["envios_riesgo_alto"]
            if altos:
                _grafico(_barras("Envíos de riesgo alto: probabilidad de demora", altos, "id_envio", "probabilidad_demora"))
            tabla_simple("Envíos de riesgo alto", altos)

    async def cargar_transporte() -> None:
        d = await _datos((servicio_tramo.costos_por_medio_transporte,), (servicio.ranking_clientes_por_volumen, 10))
        if d is None:
            return
        costos, clientes = d
        with paneles["Transporte y clientes"]:
            if costos:
                _grafico(_barras("Costo total por medio de transporte", costos, "medio_transporte", "costo_total"))
            tabla_simple("Costos por medio de transporte", costos)
            if clientes:
                _grafico(_barras("Clientes por volumen (contenedores)", clientes, "razon_social", "volumen_total"))
            tabla_simple("Ranking de clientes por volumen", clientes)

    cargadores = {
        "Envíos": cargar_envios, "Incidentes": cargar_incidentes, "Desempeño histórico": cargar_desempeno,
        "Riesgo de atrasos": cargar_riesgo, "Transporte y clientes": cargar_transporte,
    }

    async def cargar(nombre) -> None:
        if nombre not in cargadores:
            nombre = nombres[0]
        paneles[nombre].clear()
        await cargadores[nombre]()

    async def recalcular() -> None:
        ok, predicciones = await llamar(servicio_ml.calcular_predicciones)
        if ok:
            ui.notify(f"Se calcularon {len(predicciones)} predicciones.", type="positive")
            await cargar("Riesgo de atrasos")

    boton_ml.on_click(recalcular)
    tabs.on_value_change(lambda e: cargar(e.value))
    await cargar(nombres[0])
