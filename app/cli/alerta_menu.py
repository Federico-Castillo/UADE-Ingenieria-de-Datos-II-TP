"""Menú ABM de Alerta (Redis, con TTL). Junto con Regla forma el "ABM Reglas y
Alertas" del checklist de promoción."""
from app.cli.io_utils import confirmar, leer_entero, leer_no_vacio, limpiar_pantalla, pausar
from app.core.exceptions import AppError
from app.domain.alerta import Alerta
from app.services.alerta_service import AlertaService


def _imprimir(a: Alerta) -> None:
    print(
        f"  [{a.id_alerta}] sensor {a.id_sensor} | regla {a.id_regla} | {a.tipo} | "
        f"{a.fecha} | {a.estado}"
    )


def _generar(service: AlertaService) -> None:
    print("\n-- Generar Alerta --")
    id_sensor = leer_entero("ID de sensor")
    id_regla = leer_entero("ID de regla que la dispara")
    alerta = service.generar_alerta(id_sensor, id_regla)
    print(f"Alerta generada: {alerta.id_alerta} (expira en 24hs si no se resuelve antes).")


def _resolver(service: AlertaService) -> None:
    print("\n-- Resolver Alerta --")
    id_alerta = leer_no_vacio("ID de alerta a resolver")
    service.resolver(id_alerta)
    print("Alerta resuelta.")


def _listar_activas(service: AlertaService) -> None:
    print("\n-- Alertas Activas --")
    alertas = service.listar_activas()
    if not alertas:
        print("  No hay alertas activas.")
    for a in alertas:
        _imprimir(a)


_ACCIONES = {
    "1": ("Generar alerta", _generar),
    "2": ("Resolver alerta", _resolver),
    "3": ("Listar alertas activas", _listar_activas),
}


def menu_alerta() -> None:
    service = AlertaService()
    while True:
        limpiar_pantalla()
        print("\n=== Gestión de Alertas ===")
        for key, (nombre, _) in _ACCIONES.items():
            print(f"{key}) {nombre}")
        print("0) Volver")
        opcion = input("Elegí una opción: ").strip()
        if opcion == "0":
            return
        accion = _ACCIONES.get(opcion)
        if accion is None:
            print("Opción inválida.")
            continue
        try:
            accion[1](service)
        except AppError as e:
            print(f"Error: {e}")
        pausar()
