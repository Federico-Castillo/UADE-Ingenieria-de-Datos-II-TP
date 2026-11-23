"""Interfaz web (NiceGUI) que reemplaza a la consola. Reutiliza los mismos
services que la CLI: no hay lógica de negocio acá.

Pantallas:
  /abm       ABM de verdad: tabla + Nuevo / Editar / Baja por entidad.
  /          Explorador: elegís un service y un método; el formulario se arma
             solo desde la firma (ABMs, consultas, procesos... todo).
  /reportes  Todos los reportes operativos y analíticos, con gráficos.
  /alertas   Alertas activas con actualización automática y resolución.
  /red       Grafo de Neo4j: red cliente–operador y ruta de un envío.
  /mapa      Recorrido GPS de un contenedor (Leaflet vía folium).
"""
import logging
import os
from datetime import datetime

from nicegui import app, run, ui

from app.core.exceptions import AppError
from app.services.mapa_service import _DIR_SALIDA
from app.services.reporte_operativo_service import ReporteOperativoService
from app.ui import abm, grafos, reflexion
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
        ui.link("Red", "/red").classes("text-white")
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


async def _confirmar(mensaje: str, detalle: str = "", *, peligro: bool = True) -> bool:
    """Diálogo Cancelar / Confirmar. Devuelve True solo si se confirmó."""
    with ui.dialog() as dialogo, ui.card().classes("min-w-[24rem]"):
        ui.label(mensaje).classes("text-base")
        if detalle:
            ui.label(detalle).classes("text-sm text-grey")
        with ui.row().classes("justify-end w-full"):
            ui.button("Cancelar", on_click=lambda: dialogo.submit(False)).props("flat")
            ui.button("Confirmar", color="negative" if peligro else "primary", on_click=lambda: dialogo.submit(True))
    resultado = await dialogo
    dialogo.delete()
    return bool(resultado)


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
    if campo.opciones:
        opciones = list(campo.opciones)
        valor = inicial if inicial not in (None, "") else (campo.default if campo.default in opciones else None)
        if valor is not None and valor not in opciones:
            opciones.append(valor)  # valor histórico que ya no está en la lista
        w = ui.select(opciones, label=etiqueta_campo, value=valor, clearable=not campo.requerido)
        if solo_lectura:
            w.props("readonly")
        return w.classes("w-72")
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
            instancia = _reg().obtener(e.value)
        except Exception as ex:
            logger.exception("No se pudo crear el service %s", e.value)
            ui.notify(f"No se pudo iniciar el service: {ex}", type="negative", multi_line=True)
            return
        ayuda.set_text("")
        sel_metodo.set_options(
            {m: reflexion.nombre_legible(m) for m in reflexion.metodos_publicos(instancia)}, value=None)

    def al_elegir_metodo(e) -> None:
        zona_resultado.clear()
        if not e.value or not sel_service.value:
            ayuda.set_text("")
            boton.set_visibility(False)
            return
        metodo = getattr(_reg().obtener(sel_service.value), e.value)
        descripcion = reflexion.descripcion_de(metodo)
        ayuda.set_text(f"{e.value}()" + (f" — {descripcion}" if descripcion else ""))
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
        riesgo = abm.riesgo_de(sel_metodo.value)
        if riesgo:
            detalle = ", ".join(f"{k}={v}" for k, v in kwargs.items())
            mensaje = ("Esta operación borra o da de baja datos." if riesgo == "baja"
                       else "Este proceso modifica datos en bloque.")
            if not await _confirmar(f"{mensaje} ¿Ejecutar {reflexion.nombre_legible(sel_metodo.value).lower()}?", detalle):
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
        with ui.expansion("Simulador de sensores IoT (para la demo)", icon="sensors").classes("w-full"):
            ui.label("Genera lecturas sintéticas (mismo generador que scripts/simulador_iot.py) y las registra: "
                     "si violan una regla se dispara Cassandra → Mongo (incidente) → Redis (alerta).").classes("text-sm text-grey")
            with ui.row().classes("items-end gap-4"):
                sel_sensor = ui.select({}, label="Sensor", with_input=True).classes("w-96")
                with ui.column().classes("gap-0"):
                    etiqueta_prob = ui.label("")
                    prob = ui.slider(min=0, max=1, step=0.1, value=1.0).classes("w-48")
                    etiqueta_prob.bind_text_from(prob, "value", lambda v: f"Probabilidad de anomalía: {v:.0%}")
                b_una = ui.button("Enviar lectura del sensor", icon="send")
                b_tick = ui.button("Tick (todos los sensores)", icon="bolt", color="secondary")
                continuo = ui.switch("Continuo cada 5 s")
            bitacora = ui.log(max_lines=60).classes("w-full h-40")
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

    # --- Simulador de sensores (reutiliza el generador del script) ---
    try:
        servicio_sensor = _reg().obtener("sensor_iot")
        servicio_lectura = _reg().obtener("lectura_sensor")
        sensores = await run.io_bound(servicio_sensor.listar)
    except Exception as ex:
        logger.exception("No se pudo preparar el simulador")
        sensores = []
        bitacora.push(f"Simulador no disponible: {ex}")
    sel_sensor.set_options({s.id_sensor: f"sensor {s.id_sensor} · {s.tipo} · contenedor {s.id_contenedor}" for s in sensores})
    por_id = {s.id_sensor: s for s in sensores}

    async def simular(lista) -> None:
        from scripts.simulador_iot import _resumen, generar_lectura
        for sensor in lista:
            lectura, es_anomalia = generar_lectura(sensor, prob.value)
            try:
                creada = await run.io_bound(servicio_lectura.registrar_lectura, lectura)
            except (AppError, ValueError) as e:
                bitacora.push(f"sensor {sensor.id_sensor}: ERROR {e}")
                continue
            marca = "  *** ANOMALÍA ***" if es_anomalia else ""
            bitacora.push(f"sensor {sensor.id_sensor} ({sensor.tipo}){marca} -> {_resumen(creada)}")
        await refrescar()

    async def simular_una() -> None:
        if sel_sensor.value not in por_id:
            ui.notify("Elegí un sensor.", type="warning")
            return
        await simular([por_id[sel_sensor.value]])

    async def simular_tick() -> None:
        if not por_id:
            ui.notify("No hay sensores dados de alta.", type="warning")
            return
        await simular(list(por_id.values()))

    b_una.on_click(simular_una)
    b_tick.on_click(simular_tick)
    ui.timer(5.0, lambda: refrescar() if auto.value and not continuo.value else None)
    ui.timer(5.0, lambda: simular_tick() if continuo.value else None)
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

    async def pedir_baja() -> None:
        c = cap()
        srv = servicio()
        obj = estado["objetos"][estado["fila"]]
        nombre_param = abm.nombre_param_baja(srv, c)
        valor = getattr(obj, nombre_param, None)
        accion = "dar de baja" if c.baja == "dar_baja" else "eliminar"
        detalle = "El borrado es definitivo." if c.baja == "eliminar" else ""
        if not await _confirmar(f"¿Seguro que querés {accion} el registro {nombre_param} = {valor}?", detalle):
            return
        ok, _ = await _llamar(getattr(srv, c.baja), valor)
        if ok:
            ui.notify("Hecho.", type="positive")
            await cargar()

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


@ui.page("/red")
async def pagina_red() -> None:
    _encabezado("Red logística (Neo4j)")
    try:
        servicio = _reg().obtener("tramo")
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
        ok, filas = await _llamar(servicio.red_relaciones)
        if not ok:
            return
        with zona_red:
            if not filas:
                ui.label("Todavía no hay relaciones cliente–operador (hacen falta tramos registrados).")
                return
            ui.echart(grafos.opciones_red(filas)).classes("w-full h-[32rem]")
            ui.label("Cada línea une un cliente con un operador que transportó alguno de sus envíos. "
                     "Los nodos se pueden arrastrar.").classes("text-sm text-grey")
            _tabla_simple("Relaciones", filas)

    async def ver_ruta() -> None:
        zona_ruta.clear()
        try:
            id_envio = int(entrada.value)
        except (TypeError, ValueError):
            ui.notify("Ingresá un ID de envío numérico.", type="warning")
            return
        ok, tramos = await _llamar(servicio.ruta_completa, id_envio)
        if not ok:
            return
        with zona_ruta:
            if not tramos:
                ui.label(f"El envío {id_envio} no tiene tramos registrados.")
                return
            ui.echart(grafos.opciones_ruta(tramos, id_envio)).classes("w-full h-72")
            _tabla_simple("Tramos", tramos)

    ui.timer(0.1, cargar_red, once=True)


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
