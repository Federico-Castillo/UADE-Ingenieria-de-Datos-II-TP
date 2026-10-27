"""Punto de entrada de la aplicación de consola."""
import logging

from app.cli.menu_principal import menu_principal
from app.core.exceptions import ConnectionConfigError
from app.logging_config import setup_logging

logger = logging.getLogger(__name__)


def main() -> None:
    try:
        setup_logging()
    except ConnectionConfigError as e:
        print(f"Error de configuración: {e}")
        return

    logger.info("Aplicación iniciada")
    try:
        menu_principal()
    except KeyboardInterrupt:
        print("\n¡Hasta luego!")
    except Exception:
        logger.exception("Error inesperado no manejado")
        print("Ocurrió un error inesperado. Revisá logs/app.log para más detalle.")
    finally:
        logger.info("Aplicación finalizada")


if __name__ == "__main__":
    main()
