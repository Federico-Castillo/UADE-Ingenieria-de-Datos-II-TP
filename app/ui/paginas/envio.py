"""Ficha 360° de un envío: MySQL, MongoDB, Neo4j, Redis y Cassandra en una sola pantalla."""
import asyncio
import logging
import os

from nicegui import run, ui

from app.ui import ficha, grafos, reflexion
from app.ui.comun import encabezado, reg

logger = logging.getLogger(__name__)


_COLOR_MOTOR = {"MySQL": "blue", "MongoDB": "green", "Neo4j": "purple", "Redis": "red", "Cassandra": "orange"}


def _tarjeta(titulo: str, motor: str, clases: str = ""):
    """Tarjeta con el motor de origen; devuelve el cuerpo (arranca con un spinner)."""
    with ui.card().classes(f"w-full {clases}"):
        with ui.row().classes("items-center gap-2"):
            ui.label(titulo).classes("font-bold")
            ui.badge(motor, color=_COLOR_MOTOR.get(motor, "grey"))
        cuerpo = ui.column().classes("w-full gap-1")
        with cuerpo:
            ui.spinner(size="sm")
    return cuerpo


def _pintar_seccion(cuerpo, seccion, render) -> None:
    cuerpo.clear()
    with cuerpo:
        if seccion.error:
            ui.label(f"No disponible: {seccion.error}").classes("text-negative")
        elif seccion.vacia:
            ui.label("Sin datos.").classes("text-grey")
        else:
            render(seccion.datos)


def _tabla_de(filas: list[dict]) -> None:
    columnas = [{"name": k, "label": k, "field": k, "align": "left"} for k in filas[0]]
    for i, f in enumerate(filas):
        f["_n"] = i
    ui.table(columns=columnas, rows=filas, row_key="_n", pagination=8).classes("w-full")


def _r_base(d: dict) -> None:
    e, c = d["envio"], d["cliente"]
    with ui.row().classes("gap-2 items-center"):
        ui.badge(e.estado)
        ui.badge(f"prioridad {e.prioridad}", color="secondary")
    ui.label(f"{e.origen} → {e.destino}").classes("text-lg")
    ui.label(f"Cliente: {c.razon_social} ({c.pais or 's/país'})" if c else f"Cliente {e.id_cliente} (no se pudo leer)")
    ui.label(f"Creado: {e.fecha_creacion}")
    if d["saldo"] is not None:
        ui.label(f"Saldo de la cuenta corriente del cliente: ${d['saldo']:,.2f}")


def _r_contenedores(items: list[dict]) -> None:
    _tabla_de([{
        "contenedor": i["contenedor"].codigo_internacional, "tipo": i["contenedor"].tipo,
        "estado": i["contenedor"].estado,
        "sensores": ", ".join(f"{s.id_sensor} {s.tipo} ({s.estado})" for s in i["sensores"]) or "(sin sensores)",
    } for i in items])


def _r_lecturas(pares: list) -> None:
    filas = []
    for sensor, lectura in pares:
        fila = {"sensor": f"{sensor.id_sensor} · {sensor.tipo}"}
        if lectura is None:
            fila["última lectura"] = "(sin lecturas)"
        else:
            for etiqueta_valor, valor in (("temp", lectura.temperatura), ("hum", lectura.humedad),
                                          ("vib", lectura.vibracion), ("bat", lectura.nivel_bateria)):
                if valor is not None:
                    fila[etiqueta_valor] = valor
            fila["gps"] = f"{lectura.gps_lat}, {lectura.gps_lon}" if lectura.gps_lat is not None else ""
            fila["fecha"] = str(lectura.fecha_hora)
        filas.append(fila)
    # las filas pueden tener columnas distintas: se unifican para la tabla
    columnas = list(dict.fromkeys(k for f in filas for k in f))
    _tabla_de([{k: f.get(k, "") for k in columnas} for f in filas])


def _r_eventos(eventos: list) -> None:
    with ui.timeline(side="right").classes("w-full"):
        for ev in eventos:
            ubicacion = f" · {ev.ubicacion}" if ev.ubicacion else ""
            ui.timeline_entry((ev.descripcion or "") + ubicacion, title=ev.tipo_evento, subtitle=str(ev.fecha_hora))


def _r_tabla_objetos(objetos: list) -> None:
    _tabla_de(reflexion.a_filas(objetos))


def _r_riesgo(p) -> None:
    ui.label(f"Probabilidad de demora: {p.probabilidad_demora:.0%}").classes("text-lg")
    ui.linear_progress(value=float(p.probabilidad_demora), show_value=False).classes("w-full")
    ui.label(f"Riesgo climático: {p.riesgo_climatico:.0%} · riesgo operativo: {p.riesgo_operativo:.0%}")
    ui.label(f"Calculada: {p.fecha_calculo}").classes("text-sm text-grey")


def _r_ruta(tramos: list, id_envio: int) -> None:
    ui.echart(grafos.opciones_ruta(tramos, id_envio)).classes("w-full h-60")
    _tabla_de(reflexion.a_filas(tramos))


@ui.page("/envio")
async def pagina_ficha(id_envio: int | None = None) -> None:
    encabezado("Ficha del envío (los 5 motores)")
    obtener = reg().obtener

    async def en_hilo(funcion, *args):
        return await run.io_bound(funcion, obtener, *args)

    try:
        envios = await run.io_bound(obtener("envio").listar)
    except Exception as ex:
        logger.exception("No se pudo listar los envíos")
        ui.notify(f"No se pudo conectar a MySQL: {ex}", type="negative", multi_line=True)
        return
    opciones = {e.id_envio: f"{e.id_envio} · {e.origen} → {e.destino} ({e.estado})" for e in envios}
    with ui.column().classes("w-full p-4 gap-3"):
        sel = ui.select(opciones, label="Envío", value=id_envio if id_envio in opciones else None,
                        with_input=True).classes("w-[28rem]")
        sel.on_value_change(lambda e: ui.navigate.to(f"/envio?id_envio={e.value}") if e.value else None)
        if id_envio is None:
            ui.label("Elegí un envío para ver todo lo que se sabe de él: MySQL, MongoDB, Neo4j, Redis y Cassandra en una sola pantalla.").classes("text-grey")
            return
        if id_envio not in opciones:
            ui.label(f"No existe el envío {id_envio}.").classes("text-negative")
            return

        cuerpo_base = _tarjeta("Envío y cliente", "MySQL")
        with ui.grid(columns=2).classes("w-full gap-3"):
            cuerpo_cont = _tarjeta("Contenedores y sensores", "MySQL")
            cuerpo_lect = _tarjeta("Última lectura de cada sensor", "Cassandra")
            cuerpo_inc = _tarjeta("Incidentes", "MongoDB")
            cuerpo_al = _tarjeta("Alertas activas del envío", "Redis")
            cuerpo_riesgo = _tarjeta("Predicción de riesgo de atraso", "MongoDB")
            cuerpo_ev = _tarjeta("Eventos logísticos", "MongoDB")
        cuerpo_ruta = _tarjeta("Ruta y tramos", "Neo4j")
        cuerpo_mapa = _tarjeta("Recorrido GPS del contenedor", "Cassandra")

    try:
        base = await en_hilo(ficha.cargar_base, id_envio)  # el envío existe: viene de la lista
    except Exception as ex:
        logger.exception("No se pudo cargar el envío %s", id_envio)
        _pintar_seccion(cuerpo_base, ficha.Seccion("base", "", "MySQL", error=str(ex) or type(ex).__name__), _r_base)
        return
    _pintar_seccion(cuerpo_base, base, _r_base)

    async def fase_contenedores():
        sec = await en_hilo(ficha.cargar_contenedores, id_envio)
        _pintar_seccion(cuerpo_cont, sec, _r_contenedores)
        lect = await en_hilo(ficha.cargar_lecturas, sec)
        _pintar_seccion(cuerpo_lect, lect, _r_lecturas)
        _preparar_mapa(cuerpo_mapa, sec)
        return sec

    async def fase_incidentes():
        sec = await en_hilo(ficha.cargar_incidentes, id_envio)
        _pintar_seccion(cuerpo_inc, sec, _r_tabla_objetos)
        return sec

    async def fase_alertas(t_cont, t_inc):
        sec = await en_hilo(ficha.cargar_alertas, await t_inc, await t_cont)
        _pintar_seccion(cuerpo_al, sec, _r_tabla_objetos)

    async def fase_simple(cargador, cuerpo, render):
        _pintar_seccion(cuerpo, await en_hilo(cargador, id_envio), render)

    t_cont = asyncio.create_task(fase_contenedores())
    t_inc = asyncio.create_task(fase_incidentes())
    await asyncio.gather(
        t_cont, t_inc, fase_alertas(t_cont, t_inc),
        fase_simple(ficha.cargar_eventos, cuerpo_ev, _r_eventos),
        fase_simple(ficha.cargar_riesgo, cuerpo_riesgo, _r_riesgo),
        fase_simple(ficha.cargar_ruta, cuerpo_ruta, lambda tramos: _r_ruta(tramos, id_envio)),
    )


def _preparar_mapa(cuerpo, contenedores) -> None:
    """Selector de contenedor + recorrido GPS (folium embebido) del primero."""
    cuerpo.clear()
    if contenedores.error or not contenedores.datos:
        with cuerpo:
            ui.label("El envío no tiene contenedores asignados." if not contenedores.error
                     else f"No disponible: {contenedores.error}").classes("text-grey")
        return
    ids = {i["contenedor"].id_contenedor: f"{i['contenedor'].id_contenedor} · {i['contenedor'].codigo_internacional}"
           for i in contenedores.datos}
    with cuerpo:
        selector = ui.select(ids, label="Contenedor", value=next(iter(ids))).classes("w-72")
        zona = ui.column().classes("w-full")

    async def mostrar() -> None:
        zona.clear()
        try:
            ruta = await run.io_bound(reg().obtener("mapa").generar_mapa_contenedor, selector.value)
        except Exception as ex:  # sin lecturas GPS, Cassandra caída...
            with zona:
                ui.label(f"Sin recorrido para mostrar: {ex}").classes("text-grey")
            return
        with zona:
            ui.element("iframe").props(f'src="/mapas/{os.path.basename(ruta)}"').classes("w-full").style(
                "height: 55vh; border: 0")

    selector.on_value_change(mostrar)
    with cuerpo:  # estas tareas corren fuera del contexto de la página: hay que entrar al slot a mano
        ui.timer(0.1, mostrar, once=True)
