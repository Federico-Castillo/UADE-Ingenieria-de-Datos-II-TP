"""Explorador: elegís un service y un método; el formulario se arma solo desde la firma
(ABMs, consultas, procesos... todo). `/?entidad=x` preselecciona la entidad."""
import logging

from nicegui import ui

from app.ui import abm, reflexion
from app.ui.comun import cargar_referencias, confirmar, construir_formulario, encabezado, leer_valores, llamar, mostrar_resultado, reg
from app.ui.registro import etiqueta

logger = logging.getLogger(__name__)


@ui.page("/")
def pagina_explorador(entidad: str = "") -> None:
    encabezado("Explorador de services")
    estado = {"widgets": {}, "parametros": []}

    with ui.column().classes("w-full p-4 gap-2"):
        with ui.row().classes("items-end gap-4"):
            sel_service = ui.select(
                {n: etiqueta(n) for n in reg().nombres()}, label="Entidad / service", with_input=True
            ).classes("w-72")
            sel_metodo = ui.select([], label="Operación").classes("w-72")
        ayuda = ui.label("").classes("text-sm text-grey")
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
            instancia = reg().obtener(e.value)
        except Exception as ex:
            logger.exception("No se pudo crear el service %s", e.value)
            ui.notify(f"No se pudo iniciar el service: {ex}", type="negative", multi_line=True)
            return
        ayuda.set_text("")
        sel_metodo.set_options(
            {m: reflexion.nombre_legible(m) for m in reflexion.metodos_publicos(instancia)}, value=None)

    async def al_elegir_metodo(e) -> None:
        zona_resultado.clear()
        if not e.value or not sel_service.value:
            ayuda.set_text("")
            boton.set_visibility(False)
            return
        metodo = getattr(reg().obtener(sel_service.value), e.value)
        descripcion = reflexion.descripcion_de(metodo)
        ayuda.set_text(f"{e.value}()" + (f" — {descripcion}" if descripcion else ""))
        estado["parametros"] = reflexion.parametros_de(metodo)
        refs = await cargar_referencias(estado["parametros"])
        estado["widgets"] = construir_formulario(zona_form, estado["parametros"], refs=refs)
        boton.set_visibility(True)

    async def ejecutar() -> None:
        metodo = getattr(reg().obtener(sel_service.value), sel_metodo.value)
        try:
            kwargs = reflexion.construir_argumentos(estado["parametros"], leer_valores(estado["widgets"]))
        except ValueError as ex:
            ui.notify(str(ex), type="warning")
            return
        riesgo = abm.riesgo_de(sel_metodo.value)
        if riesgo:
            detalle = ", ".join(f"{k}={v}" for k, v in kwargs.items())
            mensaje = ("Esta operación borra o da de baja datos." if riesgo == "baja"
                       else "Este proceso modifica datos en bloque.")
            if not await confirmar(f"{mensaje} ¿Ejecutar {reflexion.nombre_legible(sel_metodo.value).lower()}?", detalle):
                return
        ok, resultado = await llamar(metodo, **kwargs)
        if ok:
            ui.notify("Listo", type="positive")
            mostrar_resultado(zona_resultado, resultado)

    sel_service.on_value_change(al_elegir_service)
    sel_metodo.on_value_change(al_elegir_metodo)
    boton.on_click(ejecutar)
    if entidad in reg().nombres():
        sel_service.set_value(entidad)
