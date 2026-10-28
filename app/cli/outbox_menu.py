"""Menú de visibilidad/operación del Worker de Outbox (desafío de
complejidad adicional, patrón Outbox transaccional + worker asíncrono). El
worker también puede correrse como proceso separado
(worker/outbox_worker.py), igual que scripts/simulador_iot.py — este menú
sirve para inspeccionarlo y para disparar un ciclo manual durante la
defensa, sin tener que abrir otra terminal."""
from app.cli.io_utils import leer_no_vacio, limpiar_pantalla, pausar
from app.core.exceptions import AppError
from app.domain.outbox_evento import OutboxEvento
from app.services.outbox_worker_service import OutboxWorkerService


def _imprimir(e: OutboxEvento) -> None:
    print(
        f"  [{e.id_evento}] {e.entidad}:{e.id_entidad} | {e.tipo_evento} | "
        f"intentos={e.intentos} | {e.fecha_creacion}"
    )


def _ver_pendientes(service: OutboxWorkerService) -> None:
    print("\n-- Eventos Pendientes --")
    eventos = service.listar_pendientes()
    if not eventos:
        print("  No hay eventos pendientes.")
    for e in eventos:
        _imprimir(e)


def _ver_dead_letter(service: OutboxWorkerService) -> None:
    print("\n-- Eventos en Dead-Letter --")
    eventos = service.listar_dead_letter()
    if not eventos:
        print("  No hay eventos en dead-letter.")
    for e in eventos:
        _imprimir(e)


def _correr_una_vez(service: OutboxWorkerService) -> None:
    print("\n-- Correr el Worker Una Vez --")
    resultado = service.procesar_pendientes()
    print(f"Procesados: {resultado['procesados']} | Fallidos: {resultado['fallidos']} | Total: {resultado['total']}")


def _reintentar(service: OutboxWorkerService) -> None:
    print("\n-- Reintentar un Evento de Dead-Letter --")
    id_evento = leer_no_vacio("ID de evento")
    service.reintentar(id_evento)
    print("Evento movido a 'pendiente' (intentos reseteados).")


_ACCIONES = {
    "1": ("Ver eventos pendientes", _ver_pendientes),
    "2": ("Ver eventos en dead-letter", _ver_dead_letter),
    "3": ("Correr el worker una vez (procesa todos los pendientes)", _correr_una_vez),
    "4": ("Reintentar un evento de dead-letter", _reintentar),
}


def menu_outbox() -> None:
    service = OutboxWorkerService()
    while True:
        limpiar_pantalla()
        print("\n=== Worker de Outbox (sincronización MySQL -> Neo4j) ===")
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
