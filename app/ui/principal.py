"""Interfaz web (NiceGUI) que reemplaza a la consola. Reutiliza los mismos
services que la CLI: no hay lógica de negocio acá.

Pantallas:
  /          Explorador: elegís un service y un método; el formulario se arma
             solo desde la firma (ABMs, consultas, procesos... todo).
  /reportes  Gráficos de los reportes operativos.
  /mapa      Recorrido GPS de un contenedor (Leaflet vía folium).
"""
import logging
import os

from nicegui import app, run, ui

from app.core.exceptions import AppError
from app.services.mapa_service import _DIR_SALIDA
from app.services.reporte_operativo_service import ReporteOperativoService
from app.ui import reflexion
from app.ui.registro import RegistroServices, etiqueta

logger = logging.getLogger(__name__)

_registro: RegistroServices | None = None


def _reg() -> RegistroServices:
    global _registro
    if _registro is None:
        _registro = RegistroServices()
    return _registro


def _encabezado(titulo: str) -> None:
    with ui.header().classes("items-center gap-4"):
        ui.label("Persistencia Políglota").classes("text-lg font-bold")
        ui.link("Explorador", "/").classes("text-white")
        ui.link("Reportes", "/reportes").classes("text-white")
        ui.link("Mapa", "/mapa").classes("text-white")
        ui.space()
        ui.label(titulo)


async def _llamar(funcion, *args, **kwargs):
    """Ejecuta el service en un hilo (los drivers son bloqueantes) y traduce
    los errores a avisos en pantalla. Devuelve (ok, resultado)."""
    try:
        return True, await run.io_bound(lambda: funcion(*args, **kwargs))
    except (AppError, ValueError) as e:
        ui.notify(str(e), type="negative", multi_line=True)
    except Exception:
        logger.exception("Error inesperado en la UI")
        ui.notify("Error inesperado. Revisá logs/app.log.", type="negative")
    return False, None


def _mostrar_resultado(contenedor, resultado) -> None:
    contenedor.clear()
    with contenedor:
        filas = reflexion.a_filas(resultado)
        if filas is None:
            ui.label("Operación realizada." if resultado is None else str(resultado))
            return
        if not filas:
            ui.label("Sin resultados.")
            return
        columnas = [{"name": k, "label": k, "field": k, "align": "left", "sortable": True} for k in filas[0]]
        for i, fila in enumerate(filas):
            fila["_n"] = i
        ui.label(f"{len(filas)} fila(s)").classes("text-sm text-grey")
        ui.table(columns=columnas, rows=filas, row_key="_n", pagination=15).classes("w-full")


def _construir_formulario(contenedor, parametros) -> dict:
    """Dibuja los inputs y devuelve {param: widget} / {param: {campo: widget}}."""
    widgets: dict = {}
    contenedor.clear()
    with contenedor:
        if not parametros:
            ui.label("Este método no pide parámetros.").classes("text-grey")
        for p in parametros:
            if p.es_objeto:
                ui.label(etiqueta(p.nombre)).classes("font-bold mt-2")
                widgets[p.nombre] = {c.nombre: _widget_campo(c) for c in p.campos}
            else:
                widgets[p.nombre] = _widget_campo(p.campo)
    return widgets


def _widget_campo(campo):
    etiqueta_campo = campo.nombre + (" *" if campo.requerido else "")
    if campo.tipo == "bool":
        return ui.checkbox(etiqueta_campo, value=bool(campo.default))
    w = ui.input(etiqueta_campo, value="" if campo.default is None else str(campo.default))
    if campo.nota:
        w.props(f'placeholder="{campo.nota}"')
    return w.classes("w-72")


def _leer_valores(widgets: dict) -> dict:
    return {
        nombre: ({k: w.value for k, w in w_.items()} if isinstance(w_, dict) else w_.value)
        for nombre, w_ in widgets.items()
    }


@ui.page("/")
def pagina_explorador() -> None:
    _encabezado("Explorador de services")
    estado = {"widgets": {}, "parametros": []}

    with ui.column().classes("w-full p-4 gap-2"):
        with ui.row().classes("items-end gap-4"):
            sel_service = ui.select(
                {n: etiqueta(n) for n in _reg().nombres()}, label="Entidad / service", with_input=True
            ).classes("w-72")
            sel_metodo = ui.select([], label="Operación").classes("w-72")
        zona_form = ui.column().classes("gap-1")
        boton = ui.button("Ejecutar", icon="play_arrow")
        boton.set_visibility(False)
        zona_resultado = ui.column().classes("w-full")

    def al_elegir_service(e) -> None:
        zona_form.clear()
        zona_resultado.clear()
        boton.set_visibility(False)
        if not e.value:
            return
        try:
            instancia = _reg().obtener(e.value)
        except Exception as ex:
            logger.exception("No se pudo crear el service %s", e.value)
            ui.notify(f"No se pudo iniciar el service: {ex}", type="negative", multi_line=True)
            return
        sel_metodo.set_options(reflexion.metodos_publicos(instancia), value=None)

    def al_elegir_metodo(e) -> None:
        zona_resultado.clear()
        if not e.value or not sel_service.value:
            boton.set_visibility(False)
            return
        metodo = getattr(_reg().obtener(sel_service.value), e.value)
        estado["parametros"] = reflexion.parametros_de(metodo)
        estado["widgets"] = _construir_formulario(zona_form, estado["parametros"])
        boton.set_visibility(True)

    async def ejecutar() -> None:
        metodo = getattr(_reg().obtener(sel_service.value), sel_metodo.value)
        try:
            kwargs = reflexion.construir_argumentos(estado["parametros"], _leer_valores(estado["widgets"]))
        except ValueError as ex:
            ui.notify(str(ex), type="warning")
            return
        ok, resultado = await _llamar(metodo, **kwargs)
        if ok:
            ui.notify("Listo", type="positive")
            _mostrar_resultado(zona_resultado, resultado)

    sel_service.on_value_change(al_elegir_service)
    sel_metodo.on_value_change(al_elegir_metodo)
    boton.on_click(ejecutar)


def _opciones_barras(titulo: str, filas: list[dict], clave: str) -> dict:
    return {
        "title": {"text": titulo},
        "tooltip": {},
        "xAxis": {"type": "category", "data": [str(f[clave]) for f in filas]},
        "yAxis": {"type": "value"},
        "series": [{"type": "bar", "data": [f["cantidad"] for f in filas]}],
    }


@ui.page("/reportes")
async def pagina_reportes() -> None:
    _encabezado("Reportes operativos")
    contenedor = ui.row().classes("w-full p-4 gap-6")

    async def cargar() -> None:
        contenedor.clear()
        try:
            service = _reg().obtener("reporte_operativo")
        except Exception as ex:
            logger.exception("No se pudo crear ReporteOperativoService")
            ui.notify(f"No se pudo conectar a los motores: {ex}", type="negative", multi_line=True)
            return
        ok1, por_pais = await _llamar(service.envios_por_pais)
        ok2, por_estado = await _llamar(service.envios_por_estado)
        ok3, promedio = await _llamar(service.tiempo_promedio_entrega)
        with contenedor:
            if ok1:
                ui.echart(_opciones_barras("Envíos por país", por_pais, "pais")).classes("w-96 h-72")
            if ok2:
                ui.echart(_opciones_barras("Envíos por estado", por_estado, "estado")).classes("w-96 h-72")
            if ok3:
                horas = promedio["horas_promedio"]
                texto = "sin datos" if horas is None else f"{horas:.1f} h"
                ui.label(f"Tiempo promedio de entrega: {texto} ({promedio['cantidad_envios']} envíos)")

    with ui.row().classes("p-4"):
        ui.button("Actualizar", icon="refresh", on_click=cargar)
    await cargar()


@ui.page("/mapa")
def pagina_mapa() -> None:
    _encabezado("Mapa de contenedor")
    with ui.column().classes("w-full p-4"):
        entrada = ui.input("ID de contenedor").classes("w-48")
        zona = ui.column().classes("w-full")

        async def generar() -> None:
            zona.clear()
            try:
                id_contenedor = int(entrada.value)
            except (TypeError, ValueError):
                ui.notify("Ingresá un ID numérico.", type="warning")
                return
            try:
                servicio_mapa = _reg().obtener("mapa")
            except Exception as ex:
                logger.exception("No se pudo crear MapaService")
                ui.notify(f"No se pudo conectar a los motores: {ex}", type="negative", multi_line=True)
                return
            ok, ruta = await _llamar(servicio_mapa.generar_mapa_contenedor, id_contenedor)
            if ok:
                with zona:
                    ui.element("iframe").props(f'src="/mapas/{os.path.basename(ruta)}"').classes("w-full").style(
                        "height: 70vh; border: 0"
                    )

        ui.button("Mostrar recorrido", icon="map", on_click=generar)


def iniciar(puerto: int = 8090) -> None:
    os.makedirs(_DIR_SALIDA, exist_ok=True)
    app.add_static_files("/mapas", os.path.abspath(_DIR_SALIDA))
    ui.run(title="Persistencia Políglota", port=puerto, reload=False, show=True)
