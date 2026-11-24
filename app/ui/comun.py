"""Piezas compartidas por todas las pantallas: acceso a los services, encabezado con el estado
de los motores, llamadas a services con manejo de errores, diálogo de confirmación, tablas y
formularios generados por reflexión (con desplegables de valores fijos y de claves foráneas)."""
import logging

from nicegui import run, ui

from app.core.exceptions import AppError
from app.ui import abm, referencias, reflexion, salud
from app.ui.registro import etiqueta, RegistroServices

logger = logging.getLogger(__name__)


_registro: RegistroServices | None = None


def reg() -> RegistroServices:
    global _registro
    if _registro is None:
        _registro = RegistroServices()
    return _registro


def encabezado(titulo: str) -> None:
    with ui.header().classes("items-center gap-4"):
        ui.label("Persistencia Políglota").classes("text-lg font-bold")
        ui.link("ABM", "/abm").classes("text-white")
        ui.link("Explorador", "/").classes("text-white")
        ui.link("Ficha envío", "/envio").classes("text-white")
        ui.link("Reportes", "/reportes").classes("text-white")
        ui.link("Alertas", "/alertas").classes("text-white")
        ui.link("Red", "/red").classes("text-white")
        ui.link("Mapa", "/mapa").classes("text-white")
        ui.space()
        ui.label(titulo)
        with ui.row().classes("items-center gap-1"):
            chips = {m: ui.badge(m, color="grey").props("rounded") for m in salud.MOTORES}

    async def actualizar_motores() -> None:
        try:
            estado = await run.io_bound(salud.estado_rapido)
        except Exception:
            return
        for motor, ok in estado.items():
            chips[motor].props(f"color={'positive' if ok else 'negative'}")
            chips[motor].tooltip(f"{motor}: {'encendido' if ok else 'CAÍDO'}")

    ui.timer(3.0, actualizar_motores)
    ui.timer(0.2, actualizar_motores, once=True)


async def llamar(funcion, *args, **kwargs):
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


_MAX_REFERENCIAS = 500


async def cargar_referencias(parametros) -> dict[str, list[tuple]]:
    """Para cada clave foránea del formulario, la lista [(id, etiqueta)] del
    service referenciado. Si no tiene un listado simple, o falla, ese campo
    queda como texto libre (no se corta el formulario)."""
    nombres = {
        c.referencia
        for p in parametros
        for c in (p.campos if p.es_objeto else [p.campo])
        if c.referencia
    }

    def cargar(nombre: str) -> list[tuple]:
        cap = abm.detectar(reg().clase(nombre))
        if not cap.listar:
            return []
        objetos = getattr(reg().obtener(nombre), cap.listar)()
        return referencias.opciones_de_objetos(objetos[:_MAX_REFERENCIAS])

    resultado: dict[str, list[tuple]] = {}
    for nombre in sorted(nombres):
        try:
            opciones = await run.io_bound(cargar, nombre)
        except Exception:
            logger.exception("No se pudieron cargar las opciones de %s", nombre)
            continue
        if opciones:
            resultado[nombre] = opciones
    return resultado


async def confirmar(mensaje: str, detalle: str = "", *, peligro: bool = True) -> bool:
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


def mostrar_resultado(contenedor, resultado) -> None:
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


def construir_formulario(contenedor, parametros, *, ocultar=(), iniciales=None, solo_lectura=(), refs=None) -> dict:
    """Dibuja los inputs y devuelve {param: widget} / {param: {campo: widget}}.
    `ocultar`: campos que no se piden (ej. la PK en un alta). `iniciales`:
    {param: objeto} para precargar un formulario de edición. `solo_lectura`:
    campos visibles pero no editables (ej. la PK al editar). `refs`:
    {service: [(id, etiqueta)]} para mostrar las claves foráneas como desplegable."""
    widgets: dict = {}
    iniciales = iniciales or {}
    refs = refs or {}
    ocultar = set(ocultar) | abm.CAMPOS_INTERNOS
    contenedor.clear()
    with contenedor:
        if not parametros:
            ui.label("Este método no pide parámetros.").classes("text-grey")
        for p in parametros:
            if p.es_objeto:
                ui.label(etiqueta(p.nombre)).classes("font-bold mt-2")
                origen = iniciales.get(p.nombre)
                widgets[p.nombre] = {
                    c.nombre: widget_campo(
                        c, abm.texto_inicial(getattr(origen, c.nombre, None)) if origen is not None else None,
                        solo_lectura=c.nombre in solo_lectura,
                        valor_bool=getattr(origen, c.nombre, None) if origen is not None else None,
                        opciones_ref=refs.get(c.referencia),
                    )
                    for c in p.campos if c.nombre not in ocultar
                }
            else:
                widgets[p.nombre] = widget_campo(p.campo, opciones_ref=refs.get(p.campo.referencia))
    return widgets


def widget_campo(campo, inicial=None, *, solo_lectura=False, valor_bool=None, opciones_ref=None):
    etiqueta_campo = campo.nombre + (" *" if campo.requerido else "")
    if campo.tipo == "bool":
        return ui.checkbox(etiqueta_campo, value=bool(campo.default if valor_bool is None else valor_bool))
    if opciones_ref:  # clave foránea: desplegable con "id · descripción"
        opciones = {valor: texto for valor, texto in opciones_ref}
        valor = next((k for k in opciones if str(k) == str(inicial)), None) if inicial not in (None, "") else None
        if valor is None and inicial not in (None, ""):
            opciones[inicial] = f"{inicial} (no encontrado)"
            valor = inicial
        w = ui.select(opciones, label=etiqueta_campo, value=valor, with_input=True, clearable=not campo.requerido)
        if solo_lectura:
            w.props("readonly")
        return w.classes("w-72")
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


def leer_valores(widgets: dict) -> dict:
    return {
        nombre: ({k: w.value for k, w in w_.items()} if isinstance(w_, dict) else w_.value)
        for nombre, w_ in widgets.items()
    }


def tabla_simple(titulo: str, filas) -> None:
    ui.label(titulo).classes("font-bold mt-4")
    contenedor = ui.column().classes("w-full")
    mostrar_resultado(contenedor, filas)
