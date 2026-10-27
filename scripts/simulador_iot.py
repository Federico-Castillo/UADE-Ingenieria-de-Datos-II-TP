"""Simulador de sensores IoT. No hay hardware real (decisión de alcance del
TP): este script inserta lecturas sintéticas en Cassandra para los sensores
ya dados de alta (Gestión de Sensores IoT), con valores normales la mayor
parte del tiempo y anomalías ocasionales — para poder probar de punta a punta
el pipeline Cassandra -> MongoDB -> Redis de LecturaSensorService sin esperar
a que alguien cargue lecturas a mano.

Uso:
    python scripts/simulador_iot.py                        # loop cada 10s
    python scripts/simulador_iot.py --once                  # un solo tick
    python scripts/simulador_iot.py --interval 5 --anomaly-prob 0.2
"""
import argparse
import logging
import os
import random
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.exceptions import AppError
from app.domain.lectura_sensor import CAMPO_POR_TIPO_SENSOR, LecturaSensor
from app.logging_config import setup_logging
from app.repositories.sensor_iot_repository import SensorIoTRepository
from app.services.lectura_sensor_service import LecturaSensorService

logger = logging.getLogger(__name__)

# (media, desvío) para generar valores normales con distribución gaussiana.
_BASELINES = {
    "temperatura": (20.0, 3.0),
    "humedad": (55.0, 8.0),
    "vibracion": (0.5, 0.3),
    "bateria": (80.0, 10.0),
}
# (mínimo, máximo) para generar un valor que dispare una Regla típica del
# tipo correspondiente (ver reglas de ejemplo en Gestión de Reglas).
_ANOMALIAS = {
    "temperatura": (38.0, 45.0),
    "humedad": (90.0, 98.0),
    "vibracion": (5.0, 8.0),
    "bateria": (2.0, 8.0),  # batería baja es la "anomalía" para este tipo
}

# Bounding box aproximado de Sudamérica, para simular posición GPS de
# contenedores en tránsito.
_LAT_RANGE = (-55.0, -10.0)
_LON_RANGE = (-75.0, -35.0)

_posiciones: dict[int, tuple[float, float]] = {}


def _derivar_posicion(id_sensor: int) -> tuple[float, float]:
    lat, lon = _posiciones.setdefault(
        id_sensor, (random.uniform(*_LAT_RANGE), random.uniform(*_LON_RANGE))
    )
    lat += random.uniform(-0.01, 0.01)
    lon += random.uniform(-0.01, 0.01)
    _posiciones[id_sensor] = (lat, lon)
    return lat, lon


def _simular_valor(tipo_sensor: str, es_anomalia: bool) -> float:
    if es_anomalia:
        low, high = _ANOMALIAS[tipo_sensor]
        return round(random.uniform(low, high), 2)
    media, desvio = _BASELINES[tipo_sensor]
    return round(max(0.0, random.gauss(media, desvio)), 2)


def generar_lectura(sensor, prob_anomalia: float) -> tuple[LecturaSensor, bool]:
    """Genera una lectura sintética para un sensor. Devuelve la lectura y si
    se generó como anomalía intencional (para loguearlo en el tick)."""
    lat, lon = _derivar_posicion(sensor.id_sensor)
    lectura = LecturaSensor(id_sensor=sensor.id_sensor, gps_lat=round(lat, 6), gps_lon=round(lon, 6))

    campo_primario = CAMPO_POR_TIPO_SENSOR.get(sensor.tipo)
    es_anomalia = campo_primario is not None and random.random() < prob_anomalia
    if campo_primario is not None:
        setattr(lectura, campo_primario, _simular_valor(sensor.tipo, es_anomalia))

    # Batería como telemetría estándar en todo sensor, salvo que el propio
    # sensor sea de tipo "bateria" (ya la generó arriba, no se pisa).
    if campo_primario != "nivel_bateria":
        lectura.nivel_bateria = _simular_valor("bateria", False)

    return lectura, es_anomalia


def _resumen(lectura: LecturaSensor) -> str:
    partes = []
    for etiqueta, valor in (
        ("temp", lectura.temperatura),
        ("hum", lectura.humedad),
        ("vib", lectura.vibracion),
        ("bat", lectura.nivel_bateria),
    ):
        if valor is not None:
            partes.append(f"{etiqueta}={valor}")
    partes.append(f"gps=({lectura.gps_lat}, {lectura.gps_lon})")
    return ", ".join(partes)


def ejecutar_tick(service: LecturaSensorService, sensores: list, prob_anomalia: float) -> None:
    for sensor in sensores:
        lectura, es_anomalia = generar_lectura(sensor, prob_anomalia)
        try:
            creada = service.registrar_lectura(lectura)
        except AppError as e:
            logger.error("No se pudo registrar lectura del sensor %s: %s", sensor.id_sensor, e)
            continue
        marca = " *** ANOMALÍA ***" if es_anomalia else ""
        print(f"[{creada.fecha_hora}] sensor {sensor.id_sensor} ({sensor.tipo}){marca} -> {_resumen(creada)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--once", action="store_true", help="Corre un solo tick (todos los sensores) y termina")
    parser.add_argument("--interval", type=float, default=10.0, help="Segundos entre ticks (default: 10)")
    parser.add_argument(
        "--anomaly-prob", type=float, default=0.1, dest="anomaly_prob",
        help="Probabilidad de anomalía por lectura, 0.0 a 1.0 (default: 0.1)",
    )
    args = parser.parse_args()

    setup_logging()
    sensor_repo = SensorIoTRepository()
    service = LecturaSensorService()

    print(f"Simulador de sensores IoT — probabilidad de anomalía: {args.anomaly_prob:.0%}")
    try:
        while True:
            sensores = sensor_repo.listar()
            if not sensores:
                print("No hay sensores dados de alta todavía (Gestión de Sensores IoT). Esperando...")
            else:
                ejecutar_tick(service, sensores, args.anomaly_prob)
            if args.once:
                break
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nSimulador detenido.")


if __name__ == "__main__":
    main()
