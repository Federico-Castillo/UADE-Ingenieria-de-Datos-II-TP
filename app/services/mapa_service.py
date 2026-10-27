"""Visualización geográfica de las posiciones GPS de un contenedor (checklist
de Monitoreo IoT/envíos). La app es de consola — no hay ventana donde la CLI
pueda dibujar un mapa — así que la "visualización" es un archivo HTML
standalone (Leaflet, vía folium) que se abre aparte en el navegador, con el
recorrido reconstruido a partir de TODAS las lecturas de TODOS los sensores
del contenedor (ver LecturaSensorService.listar_por_contenedor)."""
import logging
import os

import folium

from app.core.exceptions import ValidationError
from app.services.lectura_sensor_service import LecturaSensorService

logger = logging.getLogger(__name__)

_DIR_SALIDA = os.path.join(os.path.dirname(__file__), "..", "..", "output", "mapas")


class MapaService:
    def __init__(self, lectura_service: LecturaSensorService | None = None):
        self._lectura_service = lectura_service or LecturaSensorService()

    def generar_mapa_contenedor(self, id_contenedor: int) -> str:
        lecturas = self._lectura_service.listar_por_contenedor(id_contenedor)
        puntos = [l for l in lecturas if l.gps_lat is not None and l.gps_lon is not None]
        if not puntos:
            raise ValidationError(f"El contenedor {id_contenedor} no tiene lecturas con posición GPS todavía.")

        centro = puntos[len(puntos) // 2]
        mapa = folium.Map(location=[centro.gps_lat, centro.gps_lon], zoom_start=5)
        folium.PolyLine([(p.gps_lat, p.gps_lon) for p in puntos], color="blue", weight=3).add_to(mapa)
        folium.Marker(
            [puntos[0].gps_lat, puntos[0].gps_lon],
            tooltip=f"Inicio: {puntos[0].fecha_hora}",
            icon=folium.Icon(color="green"),
        ).add_to(mapa)
        folium.Marker(
            [puntos[-1].gps_lat, puntos[-1].gps_lon],
            tooltip=f"Último: {puntos[-1].fecha_hora}",
            icon=folium.Icon(color="red"),
        ).add_to(mapa)
        for p in puntos[1:-1]:
            folium.CircleMarker(
                [p.gps_lat, p.gps_lon], radius=3, color="blue", fill=True,
                tooltip=f"sensor {p.id_sensor} | {p.fecha_hora}",
            ).add_to(mapa)

        os.makedirs(_DIR_SALIDA, exist_ok=True)
        ruta = os.path.join(_DIR_SALIDA, f"contenedor_{id_contenedor}.html")
        mapa.save(ruta)
        logger.info("Mapa generado para el contenedor %s en %s", id_contenedor, ruta)
        return os.path.abspath(ruta)
