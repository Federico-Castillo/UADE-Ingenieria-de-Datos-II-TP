"""Interfaz web (NiceGUI) que reemplaza a la consola. Reutiliza los mismos
services que la CLI: no hay lógica de negocio acá.

Pantallas:
  /abm       ABM de verdad: tabla + Nuevo / Editar / Baja por entidad.
  /          Explorador: elegís un service y un método; el formulario se arma
             solo desde la firma (ABMs, consultas, procesos... todo).
  /reportes  Todos los reportes operativos y analíticos, con gráficos.
  /alertas   Alertas activas con actualización automática y resolución.
  /mapa      Recorrido GPS de un contenedor (Leaflet vía folium).
"""
import logging
import os
from datetime import datetime

from nicegui import app, run, ui

from app.core.exceptions import AppError
from app.services.mapa_service import _DIR_SALIDA
from app.services.reporte_operativo_service import ReporteOperativoService
from app.ui import abm, reflexion
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
        ui.link("ABM", "/abm").classes("text-white")
        ui.link("Explorador", "/").classes("text-white")
        ui.link("Reportes", "/reportes").classes("text-white")
        ui.link("Alertas", "/alertas").classes("text-white")
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


def _construir_formulario(contenedor, parametros, *, ocultar=(), iniciales=None, solo_lectura=()) -> dict:
    """Dibuja los inputs y devuelve {param: widget} / {param: {campo: widget}}.
    `ocultar`: campos que no se piden (ej. la PK en un alta). `iniciales`:
    {param: objeto} para precargar un formulario de edición. `solo_lectura`:
    campos visibles pero no editables (ej. la PK al editar)."""
    widgets: dict = {}
    iniciales = iniciales or {}
    contenedor.clear()
    with contenedor:
        if not parametros:
            ui.label("Este método no pide parámetros.").classes("text-grey")
        for p in parametros:
            if p.es_objeto:
                ui.label(etiqueta(p.nombre)).classes("font-bold mt-2")
                origen = iniciales.get(p.nombre)
                widgets[p.nombre] = {
                    c.nombre: _widget_campo(
                        c, abm.texto_inicial(getattr(origen, c.nombre, None)) if origen is not None else None,
                        solo_lectura=c.nombre in solo_lectura,
                        valor_bool=getattr(origen, c.nombre, None) if origen is not None else None,
                    )
                    for c in p.campos if c.nombre not in ocultar
                }
            else:
                widgets[p.nombre] = _widget_campo(p.campo)
    return widgets


def _widget_campo(campo, inicial=None, *, solo_lectura=False, valor_bool=None):
    etiqueta_campo = campo.nombre + (" *" if campo.requerido else "")
    if campo.tipo == "bool":
        return ui.checkbox(etiqueta_campo, value=bool(campo.default if valor_bool is None else valor_bool))
    if inicial is None:
        sin_valor = campo.default is None or campo.tipo in ("lista", "json")
        inicial = "" if sin_valor else str(campo.default)
    w = ui.input(etiqueta_campo, value=inicial)
    if campo.nota:
        w.props(f'placeholder="{campo.nota}"')
    if "password" in campo.nombre.lower():
        w.props("type=password")
    if solo_lectura:
        w.props("readonly")
    return w.classes("w-72")


def _leer_valores(widgets: dict) -> dict:
    return {
        nombre: ({k: w.value for k, w in w_.items()} if isinstance(w_, dict) else w_.value)
        for nombre, w_ in widgets.items()
    }


@ui.page("/")
def pagina_explorador(entidad: str = "") -> None:
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
    if entidad in _reg().nombres():
        sel_service.set_value(entidad)


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


def _tabla_simple(titulo: str, filas) -> None:
    ui.label(titulo).classes("font-bold mt-4")
    contenedor = ui.column().classes("w-full")
    _mostrar_resultado(contenedor, filas)


@ui.page("/reportes")
async def pagina_reportes() -> None:
    _encabezado("Reportes operativos y analíticos")
    try:
        servicio = _reg().obtener("reporte_operativo")
        servicio_tramo = _reg().obtener("tramo")
        servicio_ml = _reg().obtener("prediccion_ml")
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
            ok, r = await _llamar(f, *args)
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
            _tabla_simple("Envíos por cliente", por_cliente)
            _tabla_simple("Tiempos de entrega por cliente (horas)", tiempos)
            _tabla_simple("Envíos demorados", demorados)

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
            _tabla_simple("Incidentes promedio por cliente", por_cliente)
            _tabla_simple("Ranking de rutas con más incidentes", rutas)
            _tabla_simple("Incidentes abiertos", abiertos)

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
            _tabla_simple("Detalle mensual", historico)

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
            _tabla_simple("Envíos de riesgo alto", altos)

    async def cargar_transporte() -> None:
        d = await _datos((servicio_tramo.costos_por_medio_transporte,), (servicio.ranking_clientes_por_volumen, 10))
        if d is None:
            return
        costos, clientes = d
        with paneles["Transporte y clientes"]:
            if costos:
                _grafico(_barras("Costo total por medio de transporte", costos, "medio_transporte", "costo_total"))
            _tabla_simple("Costos por medio de transporte", costos)
            if clientes:
                _grafico(_barras("Clientes por volumen (contenedores)", clientes, "razon_social", "volumen_total"))
            _tabla_simple("Ranking de clientes por volumen", clientes)

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
        ok, predicciones = await _llamar(servicio_ml.calcular_predicciones)
        if ok:
            ui.notify(f"Se calcularon {len(predicciones)} predicciones.", type="positive")
            await cargar("Riesgo de atrasos")

    boton_ml.on_click(recalcular)
    tabs.on_value_change(lambda e: cargar(e.value))
    await cargar(nombres[0])


@ui.page("/alertas")
async def pagina_alertas() -> None:
    _encabezado("Alertas activas (en vivo)")
    try:
        servicio = _reg().obtener("alerta")
    except Exception as ex:
        logger.exception("No se pudo crear AlertaService")
        ui.notify(f"No se pudo conectar a los motores: {ex}", type="negative", multi_line=True)
        return

    with ui.column().classes("w-full p-4 gap-2"):
        with ui.row().classes("items-center gap-4"):
            resumen = ui.label("").classes("text-lg")
            auto = ui.checkbox("Actualizar cada 5 s", value=True)
            ui.button("Actualizar ahora", icon="refresh", on_click=lambda: refrescar())
        selector = ui.select([], label="Alerta a resolver").classes("w-96")
        boton = ui.button("Marcar como resuelta", icon="check", color="positive")
        zona = ui.column().classes("w-full")

    async def refrescar() -> None:
        try:
            alertas = await run.io_bound(servicio.listar_activas)
        except Exception as ex:
            logger.exception("Error listando alertas")
            resumen.set_text(f"No se pudieron leer las alertas: {ex}")
            return
        resumen.set_text(f"{len(alertas)} alerta(s) activa(s) — {datetime.now():%H:%M:%S}")
        selector.set_options({a.id_alerta: f"{a.id_alerta} | sensor {a.id_sensor} | regla {a.id_regla}" for a in alertas})
        _mostrar_resultado(zona, alertas)

    async def resolver() -> None:
        if not selector.value:
            ui.notify("Elegí una alerta.", type="warning")
            return
        ok, _ = await _llamar(servicio.resolver, selector.value)
        if ok:
            ui.notify("Alerta resuelta.", type="positive")
            selector.set_value(None)
            await refrescar()

    boton.on_click(resolver)
    ui.timer(5.0, lambda: refrescar() if auto.value else None)
    await refrescar()


def _entidades_abm() -> dict[str, abm.Capacidades]:
    """Services con listado, detectados sobre la clase (sin conectarse a los motores)."""
    detectadas = {n: abm.detectar(_reg().clase(n)) for n in _reg().nombres()}
    return {n: c for n, c in detectadas.items() if c.es_abm}


@ui.page("/abm")
def pagina_abm(entidad: str = "") -> None:
    _encabezado("ABM de entidades")
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
            b_mas = ui.button("Más operaciones de esta entidad", icon="tune", color="secondary").props("flat")
        resumen = ui.label("Elegí una entidad.").classes("text-sm text-grey")
        zona_tabla = ui.column().classes("w-full")

    def cap() -> abm.Capacidades:
        return entidades[sel.value]

    def servicio():
        return _reg().obtener(sel.value)

    def actualizar_botones() -> None:
        hay = sel.value in entidades
        c = cap() if hay else None
        b_nuevo.set_visibility(bool(c and c.alta))
        b_editar.set_visibility(bool(c and c.modificar))
        b_baja.set_visibility(bool(c and c.baja))
        b_mas.set_visibility(hay)
        entrada_buscar.set_visibility(bool(c and c.buscar))
        boton_buscar.set_visibility(bool(c and c.buscar))
        con_fila = estado["fila"] is not None
        b_editar.set_enabled(con_fila)
        b_baja.set_enabled(con_fila)
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
                filtros["parametros"], _leer_valores(filtros["widgets"]))
        except ValueError as ex:
            ui.notify(str(ex), type="warning")
            return
        ok, objetos = await _llamar(getattr(srv, cap().listar), **kwargs)
        if ok:
            pintar(objetos)

    async def buscar() -> None:
        texto = (entrada_buscar.value or "").strip()
        if not texto:
            await cargar()
            return
        ok, objetos = await _llamar(getattr(servicio(), cap().buscar), texto)
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
        clase = _reg().clase(sel.value)
        filtros["parametros"] = reflexion.parametros_de(getattr(clase, cap().listar))
        filtros["widgets"] = _construir_formulario(zona_filtros, filtros["parametros"])
        if not filtros["parametros"]:
            zona_filtros.clear()
        await cargar()

    def abrir_formulario(modo: str) -> None:
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
        titulo = f"{'Nuevo' if modo == 'alta' else 'Editar'} — {etiqueta(sel.value)}"
        with ui.dialog() as dialogo, ui.card().classes("min-w-[30rem]"):
            ui.label(titulo).classes("text-lg font-bold")
            zona = ui.column().classes("gap-1 max-h-[60vh] overflow-auto")
            widgets = _construir_formulario(
                zona, parametros,
                ocultar={pk} if modo == "alta" and pk else (),
                iniciales=iniciales,
                solo_lectura={pk} if modo == "editar" and pk else (),
            )
            with ui.row().classes("justify-end w-full"):
                ui.button("Cancelar", on_click=dialogo.close).props("flat")

                async def guardar() -> None:
                    try:
                        kwargs = reflexion.construir_argumentos(parametros, _leer_valores(widgets))
                    except ValueError as ex:
                        ui.notify(str(ex), type="warning")
                        return
                    ok, _ = await _llamar(metodo, **kwargs)
                    if ok:
                        ui.notify("Guardado.", type="positive")
                        dialogo.close()
                        await cargar()

                ui.button("Guardar", icon="save", on_click=guardar)
        dialogo.on("hide", dialogo.delete)
        dialogo.open()

    def pedir_baja() -> None:
        c = cap()
        srv = servicio()
        obj = estado["objetos"][estado["fila"]]
        nombre_param = abm.nombre_param_baja(srv, c)
        valor = getattr(obj, nombre_param, None)
        accion = "dar de baja" if c.baja == "dar_baja" else "eliminar"
        with ui.dialog() as dialogo, ui.card():
            ui.label(f"¿Seguro que querés {accion} el registro {nombre_param} = {valor}?").classes("text-base")
            if c.baja == "eliminar":
                ui.label("El borrado es definitivo.").classes("text-sm text-negative")
            with ui.row().classes("justify-end w-full"):
                ui.button("Cancelar", on_click=dialogo.close).props("flat")

                async def confirmar() -> None:
                    ok, _ = await _llamar(getattr(srv, c.baja), valor)
                    if ok:
                        ui.notify("Hecho.", type="positive")
                        dialogo.close()
                        await cargar()

                ui.button("Confirmar", color="negative", on_click=confirmar)
        dialogo.on("hide", dialogo.delete)
        dialogo.open()

    sel.on_value_change(al_elegir_entidad)
    boton_buscar.on_click(buscar)
    entrada_buscar.on("keydown.enter", buscar)
    b_nuevo.on_click(lambda: abrir_formulario("alta"))
    b_editar.on_click(lambda: abrir_formulario("editar"))
    b_baja.on_click(pedir_baja)
    b_mas.on_click(lambda: ui.navigate.to(f"/?entidad={sel.value}"))
    actualizar_botones()
    if sel.value in entidades:
        ui.timer(0.1, al_elegir_entidad, once=True)


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
