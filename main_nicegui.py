"""Punto de entrada de la interfaz web (NiceGUI). La CLI sigue en main.py."""
import logging

from app.core.exceptions import ConnectionConfigError
from app.logging_config import setup_logging

logger = logging.getLogger(__name__)


def _informar_motores() -> None:
    """Imprime qué motores responden. Si alguno está caído la UI arranca igual
    (el encabezado lo marca en rojo y cada pantalla avisa el error), porque
    apagar un motor a propósito es parte de la demo de rollback."""
    from app.ui.salud import verificar_todos

    print("Verificando los 5 motores...")
    resultado = verificar_todos()
    for motor, (ok, detalle) in resultado.items():
        print(f"  [{'OK' if ok else 'CAÍDO'}] {motor}" + ("" if ok else f" -> {detalle}"))
    caidos = [m for m, (ok, _) in resultado.items() if not ok]
    if caidos:
        print(
            f"\nATENCIÓN: no responde {', '.join(caidos)}. Las pantallas que lo usan van a mostrar un error.\n"
            "Si todavía no los levantaste: `docker-compose up -d` y, la primera vez, "
            "`python scripts/schema/init_all.py` (Neo4j y Cassandra tardan en estar listos)."
        )
        logger.warning("UI web iniciando con motores caídos: %s", ", ".join(caidos))
    print()


def main() -> None:
    try:
        setup_logging()
    except ConnectionConfigError as e:
        print(f"Error de configuración: {e}")
        return

    _informar_motores()

    from app.ui.principal import iniciar

    logger.info("UI web iniciada")
    iniciar()


if __name__ in {"__main__", "__mp_main__"}:
    main()
