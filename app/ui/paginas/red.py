"""Grafo de Neo4j: red cliente-operador y ruta de un envío."""
import logging

from nicegui import ui

from app.ui import grafos
from app.ui.comun import encabezado, llamar, reg, tabla_simple

logger = logging.getLogger(__name__)


@ui.page("/red")
async def pagina_red() -> None:
    encabezado("Red logística (Neo4j)")
    try:
        servicio = reg().obtener("tramo")
    except Exception as ex:
        logger.exception("No se pudo crear TramoService")
        ui.notify(f"No se pudo conectar a los motores: {ex}", type="negative", multi_line=True)
        return

    with ui.tabs().classes("w-full") as tabs:
        t_red = ui.tab("Red cliente–operador")
        t_ruta = ui.tab("Ruta de un envío")
    with ui.tab_panels(tabs, value=t_red).classes("w-full"):
        with ui.tab_panel(t_red):
            zona_red = ui.column().classes("w-full gap-2")
        with ui.tab_panel(t_ruta):
            with ui.row().classes("items-end gap-4"):
                entrada = ui.input("ID de envío").classes("w-40")
                ui.button("Ver ruta", icon="alt_route", on_click=lambda: ver_ruta())
            zona_ruta = ui.column().classes("w-full gap-2")

    async def cargar_red() -> None:
        zona_red.clear()
        ok, filas = await llamar(servicio.red_relaciones)
        if not ok:
            return
        with zona_red:
            if not filas:
                ui.label("Todavía no hay relaciones cliente–operador (hacen falta tramos registrados).")
                return
            ui.echart(grafos.opciones_red(filas)).classes("w-full h-[32rem]")
            ui.label("Cada línea une un cliente con un operador que transportó alguno de sus envíos. "
                     "Los nodos se pueden arrastrar.").classes("text-sm text-grey")
            tabla_simple("Relaciones", filas)

    async def ver_ruta() -> None:
        zona_ruta.clear()
        try:
            id_envio = int(entrada.value)
        except (TypeError, ValueError):
            ui.notify("Ingresá un ID de envío numérico.", type="warning")
            return
        ok, tramos = await llamar(servicio.ruta_completa, id_envio)
        if not ok:
            return
        with zona_ruta:
            if not tramos:
                ui.label(f"El envío {id_envio} no tiene tramos registrados.")
                return
            ui.echart(grafos.opciones_ruta(tramos, id_envio)).classes("w-full h-72")
            tabla_simple("Tramos", tramos)

    ui.timer(0.1, cargar_red, once=True)
