"""Alertas activas con actualización automática y resolución, más el simulador de sensores IoT."""
import logging
from datetime import datetime

from nicegui import run, ui

from app.core.exceptions import AppError
from app.ui.comun import encabezado, llamar, mostrar_resultado, reg

logger = logging.getLogger(__name__)


@ui.page("/alertas")
async def pagina_alertas() -> None:
    encabezado("Alertas activas (en vivo)")
    try:
        servicio = reg().obtener("alerta")
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
        mostrar_resultado(zona, alertas)

    async def resolver() -> None:
        if not selector.value:
            ui.notify("Elegí una alerta.", type="warning")
            return
        ok, _ = await llamar(servicio.resolver, selector.value)
        if ok:
            ui.notify("Alerta resuelta.", type="positive")
            selector.set_value(None)
            await refrescar()

    boton.on_click(resolver)

    # --- Simulador de sensores (reutiliza el generador del script) ---
    try:
        servicio_sensor = reg().obtener("sensor_iot")
        servicio_lectura = reg().obtener("lectura_sensor")
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
