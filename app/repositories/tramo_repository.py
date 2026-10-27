"""Acceso a datos de Tramo contra Neo4j. El alta hace MERGE de los nodos
livianos :Cliente/:Envio/:Vehiculo/:Operador (con los datos que trae el
Service desde MySQL, que es la fuente de verdad) y crea el :Tramo con sus
relaciones — todo en una sola consulta Cypher. id_tramo se genera como UUID
porque Tramo no tiene tabla espejo en MySQL (no hay AUTO_INCREMENT posible)."""
import logging
import uuid

from neo4j.exceptions import Neo4jError

from app.core.exceptions import RepositoryError
from app.db.neo4j_driver import session
from app.domain.tramo import Tramo

logger = logging.getLogger(__name__)

_CREAR_TRAMO = """
MERGE (c:Cliente {id_cliente: $id_cliente})
ON CREATE SET c.razon_social = $cliente_razon_social
ON MATCH SET c.razon_social = $cliente_razon_social
MERGE (e:Envio {id_envio: $id_envio})
ON CREATE SET e.estado = $envio_estado, e.prioridad = $envio_prioridad
ON MATCH SET e.estado = $envio_estado, e.prioridad = $envio_prioridad
MERGE (c)-[:SOLICITA]->(e)
WITH e
OPTIONAL MATCH (e)-[r:INCLUYE]->(:Tramo)
WITH e, coalesce(max(r.orden), 0) + 1 AS siguiente_orden
CREATE (t:Tramo {
    id_tramo: $id_tramo,
    medio_transporte: $medio_transporte,
    fecha_salida: $fecha_salida,
    fecha_llegada_estimada: $fecha_llegada_estimada,
    costo: $costo
})
MERGE (e)-[:INCLUYE {orden: siguiente_orden}]->(t)
MERGE (origen:Ubicacion {nombre: $origen_nombre})
ON CREATE SET origen.pais = $origen_pais, origen.lat = $origen_lat, origen.lon = $origen_lon
MERGE (t)-[:ORIGEN]->(origen)
MERGE (destino:Ubicacion {nombre: $destino_nombre})
ON CREATE SET destino.pais = $destino_pais, destino.lat = $destino_lat, destino.lon = $destino_lon
MERGE (t)-[:DESTINO]->(destino)
MERGE (v:Vehiculo {id_vehiculo: $id_vehiculo})
ON CREATE SET v.tipo = $vehiculo_tipo, v.identificacion = $vehiculo_identificacion
MERGE (t)-[:TRANSPORTADO_POR]->(v)
MERGE (o:Operador {id_operador_logistico: $id_operador_logistico})
ON CREATE SET o.nombre = $operador_nombre
MERGE (v)-[:OPERADO_POR]->(o)
RETURN siguiente_orden AS orden
"""

# Consulta avanzada "ruta completa de un envío", tal cual modelado.md.
_RUTA_COMPLETA = """
MATCH (e:Envio {id_envio: $id_envio})-[r:INCLUYE]->(t:Tramo)
OPTIONAL MATCH (t)-[:ORIGEN]->(origen:Ubicacion)
OPTIONAL MATCH (t)-[:DESTINO]->(destino:Ubicacion)
OPTIONAL MATCH (t)-[:TRANSPORTADO_POR]->(v:Vehiculo)
RETURN t.id_tramo AS id_tramo, t.medio_transporte AS medio_transporte,
       t.fecha_salida AS fecha_salida, t.fecha_llegada_estimada AS fecha_llegada_estimada,
       r.orden AS orden, origen.nombre AS origen, destino.nombre AS destino,
       v.identificacion AS vehiculo
ORDER BY r.orden
"""

# Consulta avanzada "red de relaciones cliente-operador-envío", tal cual modelado.md.
_RED_RELACIONES = """
MATCH (c:Cliente)-[:SOLICITA]->(e:Envio)-[:INCLUYE]->(:Tramo)-[:TRANSPORTADO_POR]->(:Vehiculo)-[:OPERADO_POR]->(o:Operador)
RETURN DISTINCT c.id_cliente AS id_cliente, c.razon_social AS cliente,
       o.id_operador_logistico AS id_operador_logistico, o.nombre AS operador
ORDER BY cliente
"""

# Reporte analítico "costos por tipo de transporte": agregación nativa de
# Neo4j agrupando por medio_transporte, ignorando los tramos sin costo
# cargado (campo opcional).
_COSTOS_POR_MEDIO = """
MATCH (t:Tramo) WHERE t.costo IS NOT NULL
RETURN t.medio_transporte AS medio_transporte, count(t) AS cantidad_tramos,
       avg(t.costo) AS costo_promedio, sum(t.costo) AS costo_total
ORDER BY medio_transporte
"""


class TramoRepository:
    def crear(
        self,
        tramo: Tramo,
        cliente_razon_social: str,
        envio_estado: str,
        envio_prioridad: str,
        vehiculo_tipo: str,
        vehiculo_identificacion: str,
        operador_nombre: str,
        id_cliente: int,
    ) -> Tramo:
        try:
            id_tramo = uuid.uuid4().hex
            with session() as sess:
                result = sess.run(
                    _CREAR_TRAMO,
                    id_cliente=id_cliente,
                    cliente_razon_social=cliente_razon_social,
                    id_envio=tramo.id_envio,
                    envio_estado=envio_estado,
                    envio_prioridad=envio_prioridad,
                    id_tramo=id_tramo,
                    medio_transporte=tramo.medio_transporte,
                    fecha_salida=tramo.fecha_salida,
                    fecha_llegada_estimada=tramo.fecha_llegada_estimada,
                    costo=tramo.costo,
                    origen_nombre=tramo.origen_nombre,
                    origen_pais=tramo.origen_pais,
                    origen_lat=tramo.origen_lat,
                    origen_lon=tramo.origen_lon,
                    destino_nombre=tramo.destino_nombre,
                    destino_pais=tramo.destino_pais,
                    destino_lat=tramo.destino_lat,
                    destino_lon=tramo.destino_lon,
                    id_vehiculo=tramo.id_vehiculo,
                    vehiculo_tipo=vehiculo_tipo,
                    vehiculo_identificacion=vehiculo_identificacion,
                    id_operador_logistico=tramo.id_operador_logistico,
                    operador_nombre=operador_nombre,
                )
                record = result.single()
                tramo.id_tramo = id_tramo
                tramo.orden = record["orden"]
                return tramo
        except Neo4jError as e:
            logger.exception("Error creando tramo")
            raise RepositoryError(f"No se pudo crear el tramo: {e}") from e

    def ruta_completa(self, id_envio: int) -> list[dict]:
        try:
            with session() as sess:
                result = sess.run(_RUTA_COMPLETA, id_envio=id_envio)
                return [dict(r) for r in result]
        except Neo4jError as e:
            logger.exception("Error obteniendo ruta completa del envío")
            raise RepositoryError(f"No se pudo obtener la ruta del envío: {e}") from e

    def red_relaciones(self) -> list[dict]:
        try:
            with session() as sess:
                result = sess.run(_RED_RELACIONES)
                return [dict(r) for r in result]
        except Neo4jError as e:
            logger.exception("Error obteniendo la red de relaciones")
            raise RepositoryError(f"No se pudo obtener la red de relaciones: {e}") from e

    def costos_por_medio_transporte(self) -> list[dict]:
        try:
            with session() as sess:
                result = sess.run(_COSTOS_POR_MEDIO)
                return [dict(r) for r in result]
        except Neo4jError as e:
            logger.exception("Error calculando costos por medio de transporte")
            raise RepositoryError(f"No se pudo calcular los costos por medio de transporte: {e}") from e
