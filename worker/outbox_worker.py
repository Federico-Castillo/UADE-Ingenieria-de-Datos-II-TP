"""Worker asíncrono del patrón Outbox (desafío de complejidad adicional,
punto 4). Corre como proceso separado de la app, igual en espíritu a
scripts/simulador_iot.py: lee outbox_eventos pendientes y propaga los
cambios de Cliente/Envio a Neo4j vía OutboxWorkerService — nada de lógica de
persistencia nueva acá, solo el loop.

Uso:
    python worker/outbox_worker.py                # loop cada 5s hasta Ctrl+C
    python worker/outbox_worker.py --once          # un solo ciclo y termina
    python worker/outbox_worker.py --interval 10
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.logging_config import setup_logging
from app.services.outbox_worker_service import OutboxWorkerService


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--once", action="store_true", help="Procesa los pendientes una vez y termina")
    parser.add_argument("--interval", type=float, default=5.0, help="Segundos entre ciclos (default: 5)")
    args = parser.parse_args()

    setup_logging()
    service = OutboxWorkerService()
    print(f"Worker de Outbox iniciado (ciclo cada {args.interval:.0f}s, Ctrl+C para detener).")
    try:
        while True:
            resultado = service.procesar_pendientes()
            if resultado["total"]:
                print(
                    f"Ciclo: {resultado['procesados']} procesado(s), "
                    f"{resultado['fallidos']} fallido(s) de {resultado['total']}."
                )
            if args.once:
                break
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nWorker detenido.")


if __name__ == "__main__":
    main()
