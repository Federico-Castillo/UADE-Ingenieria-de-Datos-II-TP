"""Interfaz web (NiceGUI) que reemplaza a la consola. Reutiliza los mismos
services que la CLI: no hay lógica de negocio acá.

Este módulo es solo el punto de arranque; cada pantalla vive en `app/ui/paginas/`:
  /             Explorador (cualquier método de cualquier service)
  /abm          ABM por entidad: tabla + Nuevo / Editar / Baja o Cerrar
  /envio        Ficha 360° de un envío (los 5 motores)
  /reportes     Reportes operativos y analíticos con gráficos
  /alertas      Alertas activas en vivo y simulador de sensores
  /red          Grafo de Neo4j
  /mapa         Recorrido GPS de un contenedor
Las piezas compartidas están en `app/ui/comun.py`.
"""
import logging
import os

from nicegui import app, ui

from app.services.mapa_service import _DIR_SALIDA
from app.ui import paginas  # noqa: F401  (registra las rutas)

logger = logging.getLogger(__name__)


def iniciar(puerto: int = 8090) -> None:
    os.makedirs(_DIR_SALIDA, exist_ok=True)
    app.add_static_files("/mapas", os.path.abspath(_DIR_SALIDA))
    # Solo la propia máquina por defecto: la UI puede dar de baja datos y hasta
    # detener contenedores de Docker, y no tiene autenticación. Para abrirla
    # desde otro equipo hay que pedirlo a propósito con UI_HOST=0.0.0.0.
    host = os.environ.get("UI_HOST", "127.0.0.1")
    if host != "127.0.0.1":
        logger.warning("UI escuchando en %s: cualquiera con acceso a la red puede operar el sistema", host)
        print(f"ATENCIÓN: la UI escucha en {host} y no tiene autenticación; cualquiera en tu red puede usarla.")
    ui.run(title="Persistencia Políglota", host=host, port=puerto, reload=False, show=True)
