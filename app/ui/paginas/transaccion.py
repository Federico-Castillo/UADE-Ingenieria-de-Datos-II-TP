"""Demo guiada del rollback de la transacción poliglota Incidente (Mongo) + Alerta (Redis)."""
import asyncio
import logging
import subprocess

from nicegui import run, ui

from app.core.exceptions import AppError
from app.ui import salud
from app.ui.comun import confirmar, encabezado, reg

logger = logging.getLogger(__name__)


_CONTENEDOR_REDIS = "redis"  # container_name del docker-compose.yml


def _docker(accion: str) -> tuple[bool, str]:
    """`docker stop|start redis`; solo esas dos acciones sobre ese contenedor."""
    if accion not in ("stop", "start"):
        raise ValueError(accion)
    try:
        r = subprocess.run(["docker", accion, _CONTENEDOR_REDIS], capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as e:
        return False, str(e)
    return r.returncode == 0, (r.stdout + r.stderr).strip()


def _lineas_de_rollback(maximo: int = 6) -> list[str]:
    """Últimas líneas del log de la app que documentan una compensación."""
    from app.config import get_config
    try:
        with open(get_config().log_file, encoding="utf-8", errors="replace") as f:
            ultimas = f.readlines()[-3000:]
    except OSError:
        return []
    claves = ("rollback", "revierte", "Incidente eliminado")
    return [l.rstrip() for l in ultimas if any(k in l for k in claves)][-maximo:]


@ui.page("/transaccion")
async def pagina_transaccion() -> None:
    encabezado("Transacción poliglota: Incidente (Mongo) + Alerta (Redis)")
    try:
        sensor_srv = reg().obtener("sensor_iot")
        ec_srv = reg().obtener("envio_contenedor")
        lectura_srv = reg().obtener("lectura_sensor")
        incidente_srv = reg().obtener("incidente")
        alerta_srv = reg().obtener("alerta")
    except Exception as ex:
        logger.exception("No se pudieron crear los services de la demo")
        ui.notify(f"No se pudo conectar a los motores: {ex}", type="negative", multi_line=True)
        return

    with ui.column().classes("w-full p-4 gap-3 max-w-5xl"):
        ui.markdown(
            "**Qué se demuestra.** Una lectura anómala genera un *Incidente* en **MongoDB** y una *Alerta* en "
            "**Redis**. Entre dos motores distintos no existe un `COMMIT` único (2PC), así que la atomicidad se "
            "logra a mano: se confirma el incidente y, si la alerta falla, se **compensa** borrando el incidente "
            "para que no quede huérfano. La lectura en **Cassandra** nunca se pierde.\n\n"
            "**Guion:** 1) enviar con todo encendido → *COMMIT*; 2) detener Redis; 3) enviar de nuevo → "
            "*ROLLBACK* (el incidente no queda); 4) volver a iniciar Redis."
        )
        with ui.card().classes("w-full"):
            ui.label("1 · Estado de los motores involucrados").classes("font-bold")
            with ui.row().classes("items-center gap-6"):
                est_mongo = ui.label("")
                est_redis = ui.label("")
                b_stop = ui.button("Detener Redis", icon="power_off", color="negative")
                b_start = ui.button("Iniciar Redis", icon="power", color="positive")
            ui.label("Equivale a `docker stop redis` / `docker start redis`.").classes("text-xs text-grey")

        with ui.card().classes("w-full"):
            ui.label("2 · Enviar una lectura anómala").classes("font-bold")
            with ui.row().classes("items-end gap-4"):
                sel = ui.select({}, label="Sensor (con envío asignado)", with_input=True).classes("w-96")
                b_enviar = ui.button("Enviar lectura anómala", icon="bolt")

        with ui.card().classes("w-full"):
            ui.label("3 · Resultado").classes("font-bold")
            veredicto = ui.label("Todavía no se envió ninguna lectura.").classes("text-lg")
            zona_tabla = ui.column().classes("w-full")
            ui.label("Evidencia en el log de la aplicación (logs/app.log):").classes("text-sm text-grey mt-2")
            evidencia = ui.log(max_lines=10).classes("w-full h-32")

    async def refrescar_estado() -> None:
        estado = await run.io_bound(salud.estado_rapido)
        for etiqueta_motor, motor in ((est_mongo, "MongoDB"), (est_redis, "Redis")):
            etiqueta_motor.set_text(f"{motor}: {'ENCENDIDO' if estado[motor] else 'CAÍDO'}")
            etiqueta_motor.classes(
                add="text-positive" if estado[motor] else "text-negative",
                remove="text-negative" if estado[motor] else "text-positive")
        b_stop.set_enabled(estado["Redis"])
        b_start.set_enabled(not estado["Redis"])

    async def cambiar_redis(accion: str) -> None:
        texto = "detener" if accion == "stop" else "iniciar"
        if not await confirmar(f"¿{texto.capitalize()} el contenedor Redis?", f"Ejecuta: docker {accion} {_CONTENEDOR_REDIS}",
                                peligro=accion == "stop"):
            return
        ui.notify(f"Ejecutando docker {accion} {_CONTENEDOR_REDIS}…")
        ok, salida = await run.io_bound(_docker, accion)
        ui.notify(f"Redis: {texto} {'OK' if ok else 'FALLÓ: ' + salida}", type="positive" if ok else "negative", multi_line=True)
        await asyncio.sleep(1.5)
        await refrescar_estado()

    async def medir(id_envio: int, id_sensor: int) -> dict:
        def _medir() -> dict:
            incidentes = len(incidente_srv.listar_por_envio(id_envio))
            lecturas = len(lectura_srv.listar_por_sensor(id_sensor, limite=5000))
            try:
                alertas = len(alerta_srv.listar_activas())
            except Exception:  # Redis caído: no se puede leer
                alertas = None
            return {"incidentes": incidentes, "alertas": alertas, "lecturas": lecturas}
        return await run.io_bound(_medir)

    async def enviar() -> None:
        if sel.value not in sensores_por_id:
            ui.notify("Elegí un sensor.", type="warning")
            return
        sensor, id_envio = sensores_por_id[sel.value]
        b_enviar.set_enabled(False)
        try:
            from scripts.simulador_iot import generar_lectura
            antes = await medir(id_envio, sensor.id_sensor)
            lectura, _ = generar_lectura(sensor, 1.0)
            try:
                await run.io_bound(lectura_srv.registrar_lectura, lectura)
            except (AppError, ValueError) as e:
                ui.notify(f"No se pudo registrar la lectura: {e}", type="negative", multi_line=True)
                return
            despues = await medir(id_envio, sensor.id_sensor)
            redis_arriba = (await run.io_bound(salud.estado_rapido))["Redis"]
            await mostrar(antes, despues, redis_arriba, id_envio)
        finally:
            b_enviar.set_enabled(True)

    async def mostrar(antes: dict, despues: dict, redis_arriba: bool, id_envio: int) -> None:
        d_inc = despues["incidentes"] - antes["incidentes"]
        d_al = None if antes["alertas"] is None or despues["alertas"] is None else despues["alertas"] - antes["alertas"]
        if not redis_arriba:
            if d_inc == 0:
                texto, color = ("ROLLBACK confirmado: Redis está caído, la alerta no se pudo crear y el incidente "
                                "fue revertido en MongoDB (no quedó huérfano). La lectura sí quedó en Cassandra.", "text-warning")
            else:
                texto, color = "INCONSISTENCIA: el incidente quedó en MongoDB sin su alerta en Redis.", "text-negative"
        elif d_inc > 0 and d_al and d_al > 0:
            texto, color = ("COMMIT: se confirmaron el incidente (MongoDB) y la alerta (Redis), "
                            "y la lectura quedó en Cassandra.", "text-positive")
        elif d_inc == 0 and not d_al:
            texto, color = "La lectura no violó ninguna regla: no hubo incidente ni alerta.", "text-grey"
        else:
            texto, color = "ESTADO PARCIAL: revisar, los motores no quedaron coherentes entre sí.", "text-negative"
        veredicto.set_text(texto)
        veredicto.classes(remove="text-positive text-warning text-negative text-grey", add=color)
        zona_tabla.clear()

        def celda(v):
            return "no disponible (Redis caído)" if v is None else v

        filas = [
            {"medida": f"Incidentes del envío {id_envio} (MongoDB)", "antes": antes["incidentes"], "despues": despues["incidentes"]},
            {"medida": "Alertas activas (Redis)", "antes": celda(antes["alertas"]), "despues": celda(despues["alertas"])},
            {"medida": "Lecturas del sensor (Cassandra)", "antes": antes["lecturas"], "despues": despues["lecturas"]},
        ]
        with zona_tabla:
            ui.table(columns=[{"name": k, "label": k.capitalize(), "field": k, "align": "left"} for k in ("medida", "antes", "despues")],
                     rows=filas, row_key="medida").classes("w-full")
        evidencia.clear()
        for linea in await run.io_bound(_lineas_de_rollback):
            evidencia.push(linea)

    # Solo los sensores cuyo contenedor tiene un envío: ahí sí hay Incidente que transaccionar.
    sensores_por_id: dict = {}
    try:
        for s in await run.io_bound(sensor_srv.listar):
            id_envio = await run.io_bound(ec_srv.envio_actual_de_contenedor, s.id_contenedor)
            if id_envio is not None:
                sensores_por_id[s.id_sensor] = (s, id_envio)
    except Exception as ex:
        logger.exception("No se pudieron listar los sensores de la demo")
        ui.notify(f"No se pudieron leer los sensores: {ex}", type="negative", multi_line=True)
    sel.set_options({i: f"sensor {i} · {s.tipo} · contenedor {s.id_contenedor} · envío {e}" for i, (s, e) in sensores_por_id.items()})

    b_stop.on_click(lambda: cambiar_redis("stop"))
    b_start.on_click(lambda: cambiar_redis("start"))
    b_enviar.on_click(enviar)
    ui.timer(2.0, refrescar_estado)
    await refrescar_estado()
