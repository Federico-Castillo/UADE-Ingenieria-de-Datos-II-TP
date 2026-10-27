"""Worker del patrón Outbox (desafío de complejidad adicional, punto 4):
propaga a Neo4j los cambios de Cliente/Envio ya confirmados en MySQL, leyendo
outbox_eventos. No hace falta una transacción distribuida entre MySQL y
Neo4j: el evento ya quedó persistido de forma ACID junto con el cambio que
lo originó (ver ClienteRepository/EnvioRepository), así que si este worker
se cae a mitad de camino el evento sigue 'pendiente' y se reintenta en la
próxima corrida. La propagación en sí es un MERGE de Cypher (idempotente por
diseño), así que reintentar un evento que en realidad ya se había aplicado
nunca duplica nodos — resuelve directamente el problema de "duplicación por
reintentos" que describe el desafío (punto 5)."""
import logging

from neo4j.exceptions import Neo4jError

from app.core.exceptions import NotFoundError
from app.db.neo4j_driver import session as neo4j_session
from app.domain.outbox_evento import OutboxEvento
from app.repositories.outbox_repository import OutboxRepository

logger = logging.getLogger(__name__)

_MERGE_CLIENTE = """
MERGE (c:Cliente {id_cliente: $id_cliente})
SET c.razon_social = $razon_social
"""

_MERGE_ENVIO = """
MERGE (c:Cliente {id_cliente: $id_cliente})
MERGE (e:Envio {id_envio: $id_envio})
SET e.estado = $estado, e.prioridad = $prioridad
MERGE (c)-[:SOLICITA]->(e)
"""

# Borra también el/los Tramo del envío (si tenía) — sin esto, un Envío
# borrado en MySQL dejaría en Neo4j la "referencia huérfana" que describe el
# desafío (punto 5). No toca Ubicacion/Vehiculo/Operador porque esos nodos
# livianos pueden estar referenciados por tramos de OTROS envíos.
_ELIMINAR_ENVIO = """
MATCH (e:Envio {id_envio: $id_envio})
OPTIONAL MATCH (e)-[:INCLUYE]->(t:Tramo)
DETACH DELETE e, t
"""


def _propagar_cliente(sess, evento: OutboxEvento) -> None:
    sess.run(_MERGE_CLIENTE, **evento.payload)


def _propagar_envio(sess, evento: OutboxEvento) -> None:
    if evento.tipo_evento == "eliminado":
        sess.run(_ELIMINAR_ENVIO, id_envio=evento.payload["id_envio"])
    else:
        sess.run(_MERGE_ENVIO, **evento.payload)


_HANDLERS = {
    "cliente": _propagar_cliente,
    "envio": _propagar_envio,
}


class OutboxWorkerService:
    def __init__(self, repository: OutboxRepository | None = None):
        self._repo = repository or OutboxRepository()

    def procesar_pendientes(self, limite: int = 50) -> dict:
        eventos = self._repo.listar_pendientes(limite=limite)
        procesados = 0
        fallidos = 0
        for evento in eventos:
            handler = _HANDLERS.get(evento.entidad)
            if handler is None:
                logger.error(
                    "Tipo de entidad de outbox desconocido: %s (evento %s)", evento.entidad, evento.id_evento
                )
                self._repo.marcar_fallo(evento.id_evento)
                fallidos += 1
                continue
            try:
                with neo4j_session() as sess:
                    handler(sess, evento)
                self._repo.marcar_procesado(evento.id_evento)
                procesados += 1
            except Neo4jError:
                logger.exception("Error propagando el evento de outbox %s", evento.id_evento)
                self._repo.marcar_fallo(evento.id_evento)
                fallidos += 1
        return {"procesados": procesados, "fallidos": fallidos, "total": len(eventos)}

    def listar_pendientes(self, limite: int = 50) -> list[OutboxEvento]:
        return self._repo.listar_pendientes(limite=limite)

    def listar_dead_letter(self) -> list[OutboxEvento]:
        return self._repo.listar_dead_letter()

    def reintentar(self, id_evento: str) -> None:
        if not self._repo.reintentar(id_evento):
            raise NotFoundError(f"No existe un evento en dead-letter con id {id_evento}.")
