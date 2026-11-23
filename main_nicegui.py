"""Punto de entrada de la interfaz web (NiceGUI). La CLI sigue en main.py."""
import logging

from app.core.exceptions import ConnectionConfigError
from app.logging_config import setup_logging

logger = logging.getLogger(__name__)


def main() -> None:
    try:
        setup_logging()
    except ConnectionConfigError as e:
        print(f"Error de configuración: {e}")
        return

    from app.ui.principal import iniciar

    logger.info("UI web iniciada")
    iniciar()


if __name__ in {"__main__", "__mp_main__"}:
    main()
