from dataclasses import dataclass
from datetime import datetime


@dataclass
class Tramo:
    """Vive únicamente en Neo4j (no tiene tabla espejo en MySQL). Los campos
    origen_*/destino_*/vehiculo_*/operador_* son los datos mínimos para
    proyectar (MERGE) los nodos livianos :Ubicacion/:Vehiculo/:Operador que
    conecta — su fuente de verdad completa sigue viviendo en MySQL."""
    id_envio: int
    medio_transporte: str
    id_vehiculo: int
    id_operador_logistico: int
    origen_nombre: str
    destino_nombre: str
    origen_pais: str | None = None
    origen_lat: float | None = None
    origen_lon: float | None = None
    destino_pais: str | None = None
    destino_lat: float | None = None
    destino_lon: float | None = None
    fecha_salida: datetime | None = None
    fecha_llegada_estimada: datetime | None = None
    costo: float | None = None
    orden: int | None = None
    id_tramo: str | None = None
