"""Acceso a datos de OutboxEvento contra MySQL — patrón Outbox transaccional
(desafío de complejidad adicional, punto 4). `encolar()` es distinto del
resto de los Repository de este proyecto: recibe el *cursor* de una
transacción que el caller (ClienteRepository/EnvioRepository) ya tiene
abierta, en vez de abrir su propia conexión. Así el INSERT en
outbox_eventos queda en la MISMA transacción ACID que el cambio que lo
origina — si esa transacción hace rollback, el evento tampoco queda
encolado; si hace commit, el evento está garantizado en la base aunque el
proceso se caiga un instante después, antes de propagarlo a Neo4j."""
import json
import logging
import uuid

from mysql.connector import Error as MySQLError

from app.core.exceptions import RepositoryError
from app.db.mysql import get_cursor, transaction
from app.domain.outbox_evento import OutboxEvento

logger = logging.getLogger(__name__)

_MAX_INTENTOS_DEFAULT = 5


def _row_to_evento(row: dict) -> OutboxEvento:
    payload = row["payload"]
    return OutboxEvento(
        id_evento=row["id_evento"],
        entidad=row["entidad"],
        id_entidad=row["id_entidad"],
        tipo_evento=row["tipo_evento"],
        payload=json.loads(payload) if isinstance(payload, str) else payload,
        estado=row["estado"],
        intentos=row["intentos"],
        fecha_creacion=row["fecha_creacion"],
        fecha_procesado=row["fecha_procesado"],
    )


class OutboxRepository:
    def encolar(self, cursor, entidad: str, id_entidad: int, tipo_evento: str, payload: dict) -> str:
        id_evento = uuid.uuid4().hex
        cursor.execute(
            """
            INSERT INTO outbox_eventos (id_evento, entidad, id_entidad, tipo_evento, payload)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (id_evento, entidad, id_entidad, tipo_evento, json.dumps(payload)),
        )
        return id_evento

    def listar_pendientes(self, limite: int = 50) -> list[OutboxEvento]:
        try:
            with get_cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM outbox_eventos WHERE estado = 'pendiente' ORDER BY fecha_creacion LIMIT %s",
                    (limite,),
                )
                return [_row_to_evento(row) for row in cursor.fetchall()]
        except MySQLError as e:
            logger.exception("Error listando eventos pendientes del outbox")
            raise RepositoryError(f"No se pudieron listar los eventos pendientes: {e}") from e

    def listar_dead_letter(self) -> list[OutboxEvento]:
        try:
            with get_cursor() as cursor:
                cursor.execute("SELECT * FROM outbox_eventos WHERE estado = 'dead_letter' ORDER BY fecha_creacion")
                return [_row_to_evento(row) for row in cursor.fetchall()]
        except MySQLError as e:
            logger.exception("Error listando eventos en dead-letter")
            raise RepositoryError(f"No se pudieron listar los eventos en dead-letter: {e}") from e

    def marcar_procesado(self, id_evento: str) -> None:
        try:
            with transaction() as cursor:
                cursor.execute(
                    "UPDATE outbox_eventos SET estado = 'procesado', fecha_procesado = CURRENT_TIMESTAMP "
                    "WHERE id_evento = %s",
                    (id_evento,),
                )
        except MySQLError as e:
            logger.exception("Error marcando evento del outbox como procesado")
            raise RepositoryError(f"No se pudo marcar el evento como procesado: {e}") from e

    def marcar_fallo(self, id_evento: str, max_intentos: int = _MAX_INTENTOS_DEFAULT) -> None:
        """Incrementa intentos; si llega al máximo pasa a 'dead_letter' en
        vez de seguir reintentando para siempre (punto 6 del desafío:
        reintentos + dead-letter queue). El espaciado entre reintentos
        ("backoff") lo da el propio intervalo de polling del worker, no un
        timestamp de "próximo intento" dedicado — simplificación razonable
        para el volumen de eventos de este TP."""
        try:
            with transaction() as cursor:
                cursor.execute(
                    """
                    UPDATE outbox_eventos
                    SET estado = IF(intentos + 1 >= %s, 'dead_letter', 'pendiente'),
                        intentos = intentos + 1
                    WHERE id_evento = %s
                    """,
                    (max_intentos, id_evento),
                )
        except MySQLError as e:
            logger.exception("Error registrando el fallo de un evento del outbox")
            raise RepositoryError(f"No se pudo registrar el fallo del evento: {e}") from e

    def reintentar(self, id_evento: str) -> bool:
        """Mueve un evento de 'dead_letter' de nuevo a 'pendiente' y resetea
        sus intentos, para reintento manual tras revisar la causa del
        fallo. Devuelve False si no existe o no está en dead_letter."""
        try:
            with transaction() as cursor:
                cursor.execute(
                    "UPDATE outbox_eventos SET estado = 'pendiente', intentos = 0 "
                    "WHERE id_evento = %s AND estado = 'dead_letter'",
                    (id_evento,),
                )
                return cursor.rowcount > 0
        except MySQLError as e:
            logger.exception("Error reintentando un evento del outbox")
            raise RepositoryError(f"No se pudo reintentar el evento: {e}") from e
