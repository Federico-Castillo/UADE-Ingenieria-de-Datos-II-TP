"""ABM de verdad: tabla + Nuevo / Editar / Baja (o Cerrar) por entidad."""
import logging

from nicegui import ui

from app.ui import abm, reflexion
from app.ui.comun import cargar_referencias, confirmar, construir_formulario, encabezado, leer_valores, llamar, reg
from app.ui.registro import etiqueta

logger = logging.getLogger(__name__)


def _etiqueta_corta(valor) -> str:
    texto = str(valor)
    return "…" + texto[-6:] if len(texto) > 12 else texto


def _entidades_abm() -> dict[str, abm.Capacidades]:
    """Services con listado, detectados sobre la clase (sin conectarse a los motores)."""
    detectadas = {n: abm.detectar(reg().clase(n)) for n in reg().nombres()}
    return {n: c for n, c in detectadas.items() if c.es_abm}


@ui.page("/abm")
def pagina_abm(entidad: str = "") -> None:
    encabezado("ABM de entidades")
    entidades = _entidades_abm()
    estado: dict = {"objetos": [], "fila": None}

    with ui.column().classes("w-full p-4 gap-2"):
        with ui.row().classes("items-end gap-4"):
            sel = ui.select(
                {n: etiqueta(n) for n in entidades}, label="Entidad", with_input=True,
                value=entidad if entidad in entidades else None,
            ).classes("w-72")
            zona_filtros = ui.row().classes("items-end gap-4")
            entrada_buscar = ui.input("Buscar texto").classes("w-56")
            boton_buscar = ui.button(icon="search")
            ui.button("Actualizar", icon="refresh", on_click=lambda: cargar())
        with ui.row().classes("gap-2"):
            b_nuevo = ui.button("Nuevo", icon="add", color="positive")
            b_editar = ui.button("Editar", icon="edit")
            b_baja = ui.button("Dar de baja", icon="delete", color="negative")
            b_cerrar = ui.button("Cerrar", icon="check_circle", color="positive")
            b_ficha = ui.button("Ver ficha del envío", icon="description", color="secondary")
            b_mas = ui.button("Más operaciones de esta entidad", icon="tune", color="secondary").props("flat")
        resumen = ui.label("Elegí una entidad.").classes("text-sm text-grey")
        zona_tabla = ui.column().classes("w-full")

    def cap() -> abm.Capacidades:
        return entidades[sel.value]

    def servicio():
        return reg().obtener(sel.value)

    def _ya_cerrado() -> bool:
        """El registro seleccionado ya está en el estado final del cierre."""
        if estado["fila"] is None or sel.value not in entidades or not cap().cierre:
            return False
        return getattr(estado["objetos"][estado["fila"]], "estado", None) == cap().cierre[1]

    def actualizar_botones() -> None:
        hay = sel.value in entidades
        c = cap() if hay else None
        b_nuevo.set_visibility(bool(c and c.alta))
        b_editar.set_visibility(bool(c and c.modificar))
        b_baja.set_visibility(bool(c and c.baja))
        b_cerrar.set_visibility(bool(c and c.cierre))
        b_mas.set_visibility(hay)
        b_ficha.set_visibility(sel.value == "envio")
        entrada_buscar.set_visibility(bool(c and c.buscar))
        boton_buscar.set_visibility(bool(c and c.buscar))
        con_fila = estado["fila"] is not None
        b_editar.set_enabled(con_fila)
        b_baja.set_enabled(con_fila)
        b_cerrar.set_enabled(con_fila and not _ya_cerrado())
        b_ficha.set_enabled(con_fila)
        if c and c.baja:
            b_baja.set_text("Dar de baja" if c.baja == "dar_baja" else "Eliminar")

    def seleccionar(filas: list[dict]) -> None:
        estado["fila"] = int(filas[0]["_n"]) if filas else None
        actualizar_botones()

    def pintar(objetos) -> None:
        estado["objetos"], estado["fila"] = list(objetos), None
        zona_tabla.clear()
        filas = reflexion.a_filas(estado["objetos"]) or []
        with zona_tabla:
            if not filas:
                resumen.set_text("Sin registros.")
            else:
                resumen.set_text(f"{len(filas)} registro(s). Seleccioná una fila para editar o dar de baja.")
                columnas = [{"name": k, "label": k, "field": k, "align": "left", "sortable": True} for k in filas[0]]
                for i, f in enumerate(filas):
                    f["_n"] = i
                ui.table(
                    columns=columnas, rows=filas, row_key="_n", selection="single", pagination=15,
                    on_select=lambda e: seleccionar(e.selection),
                ).classes("w-full")
        actualizar_botones()

    async def cargar() -> None:
        if sel.value not in entidades:
            return
        try:
            srv = servicio()
        except Exception as ex:
            logger.exception("No se pudo crear el service %s", sel.value)
            ui.notify(f"No se pudo conectar a los motores: {ex}", type="negative", multi_line=True)
            return
        try:
            kwargs = reflexion.construir_argumentos(
                filtros["parametros"], leer_valores(filtros["widgets"]))
        except ValueError as ex:
            ui.notify(str(ex), type="warning")
            return
        ok, objetos = await llamar(getattr(srv, cap().listar), **kwargs)
        if ok:
            pintar(objetos)

    async def buscar() -> None:
        texto = (entrada_buscar.value or "").strip()
        if not texto:
            await cargar()
            return
        ok, objetos = await llamar(getattr(servicio(), cap().buscar), texto)
        if ok:
            pintar(objetos)

    filtros: dict = {"parametros": [], "widgets": {}}

    async def al_elegir_entidad(_e=None) -> None:
        estado["fila"] = None
        zona_tabla.clear()
        entrada_buscar.set_value("")
        filtros["parametros"], filtros["widgets"] = [], {}
        zona_filtros.clear()
        actualizar_botones()
        if sel.value not in entidades:
            return
        # Parámetros opcionales del listado (ej. solo_activos): se muestran como filtros.
        clase = reg().clase(sel.value)
        filtros["parametros"] = reflexion.parametros_de(getattr(clase, cap().listar))
        filtros["widgets"] = construir_formulario(zona_filtros, filtros["parametros"])
        if not filtros["parametros"]:
            zona_filtros.clear()
        await cargar()

    async def abrir_formulario(modo: str) -> None:
        c = cap()
        srv = servicio()
        nombre_metodo = c.alta if modo == "alta" else c.modificar
        metodo = getattr(srv, nombre_metodo)
        parametros = reflexion.parametros_de(metodo)
        clase = parametros[0].clase if parametros and parametros[0].es_objeto else None
        pk = abm.clave_primaria(clase) if clase else None
        iniciales = {}
        if modo == "editar":
            iniciales = {parametros[0].nombre: estado["objetos"][estado["fila"]]}
        refs = await cargar_referencias(parametros)
        titulo = f"{'Nuevo' if modo == 'alta' else 'Editar'} — {etiqueta(sel.value)}"
        with ui.dialog() as dialogo, ui.card().classes("min-w-[30rem]"):
            ui.label(titulo).classes("text-lg font-bold")
            zona = ui.column().classes("gap-1 max-h-[60vh] overflow-auto")
            widgets = construir_formulario(
                zona, parametros,
                ocultar={pk} if modo == "alta" and pk else (),
                iniciales=iniciales,
                solo_lectura={pk} if modo == "editar" and pk else (),
                refs=refs,
            )
            with ui.row().classes("justify-end w-full"):
                ui.button("Cancelar", on_click=dialogo.close).props("flat")

                async def guardar() -> None:
                    try:
                        kwargs = reflexion.construir_argumentos(parametros, leer_valores(widgets))
                    except ValueError as ex:
                        ui.notify(str(ex), type="warning")
                        return
                    ok, _ = await llamar(metodo, **kwargs)
                    if ok:
                        ui.notify("Guardado.", type="positive")
                        dialogo.close()
                        await cargar()

                ui.button("Guardar", icon="save", on_click=guardar)
        dialogo.on("hide", dialogo.delete)
        dialogo.open()

    async def pedir_baja() -> None:
        c = cap()
        srv = servicio()
        obj = estado["objetos"][estado["fila"]]
        nombre_param = abm.nombre_param_baja(srv, c)
        valor = getattr(obj, nombre_param, None)
        accion = "dar de baja" if c.baja == "dar_baja" else "eliminar"
        detalle = "El borrado es definitivo." if c.baja == "eliminar" else ""
        if not await confirmar(f"¿Seguro que querés {accion} el registro {nombre_param} = {valor}?", detalle):
            return
        ok, _ = await llamar(getattr(srv, c.baja), valor)
        if ok:
            ui.notify("Hecho.", type="positive")
            await cargar()

    async def pedir_cierre() -> None:
        c = cap()
        metodo, estado_final = c.cierre
        obj = estado["objetos"][estado["fila"]]
        pk = abm.clave_primaria(type(obj))
        valor = getattr(obj, pk)
        if not await confirmar(
            f"¿Cerrar el registro {pk} = {_etiqueta_corta(valor)}?",
            f"Pasa a estado '{estado_final}'. No se borra: queda en el historial.", peligro=False,
        ):
            return
        ok, _ = await llamar(getattr(servicio(), metodo), valor, estado_final)
        if ok:
            ui.notify("Cerrado.", type="positive")
            await cargar()

    sel.on_value_change(al_elegir_entidad)
    b_cerrar.on_click(pedir_cierre)
    boton_buscar.on_click(buscar)
    entrada_buscar.on("keydown.enter", buscar)
    b_nuevo.on_click(lambda: abrir_formulario("alta"))
    b_editar.on_click(lambda: abrir_formulario("editar"))
    b_baja.on_click(pedir_baja)
    b_mas.on_click(lambda: ui.navigate.to(f"/?entidad={sel.value}"))
    b_ficha.on_click(lambda: ui.navigate.to(f"/envio?id_envio={estado['objetos'][estado['fila']].id_envio}"))
    actualizar_botones()
    if sel.value in entidades:
        ui.timer(0.1, al_elegir_entidad, once=True)
