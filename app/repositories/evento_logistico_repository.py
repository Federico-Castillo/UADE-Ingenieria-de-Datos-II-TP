"""Acceso a datos de EventoLogistico contra MongoDB (colección
eventos_logisticos). Un documento por evento (no embebido en el envío) porque
la cantidad de eventos por envío es ilimitada — ver modelado.md."""
import logging
from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from pymongo.errors import PyMongoError

from app.core.exceptions import RepositoryError
from app.db.mongo import get_db
from app.domain.evento_logistico import EventoLogistico

logger = logging.getLogger(__name__)

_COLLECTION = "eventos_logisticos"


def _doc_to_evento(doc: dict) -> EventoLogistico:
    return EventoLogistico(
        id_evento=str(doc["_id"]),
        id_envio=doc["id_envio"],
        tipo_evento=doc["tipo_evento"],
        descripcion=doc.get("descripcion", ""),
        ubicacion=doc.get("ubicacion"),
        fecha_hora=doc["fecha_hora"],
    )


class EventoLogisticoRepository:
    def __init__(self):
        self._collection = get_db()[_COLLECTION]

    def crear(self, evento: EventoLogistico) -> str:
        try:
            doc = {
                "id_envio": evento.id_envio,
                "tipo_evento": evento.tipo_evento,
                "descripcion": evento.descripcion,
                "fecha_hora": evento.fecha_hora or datetime.now(timezone.utc),
            }
            if evento.ubicacion:
                doc["ubicacion"] = evento.ubicacion
            result = self._collection.insert_one(doc)
            return str(result.inserted_id)
        except PyMongoError as e:
            logger.exception("Error creando evento logístico")
            raise RepositoryError(f"No se pudo crear el evento logístico: {e}") from e

    def obtener_por_id(self, id_evento: str) -> EventoLogistico | None:
        try:
            doc = self._collection.find_one({"_id": ObjectId(id_evento)})
            return _doc_to_evento(doc) if doc else None
        except InvalidId:
            return None
        except PyMongoError as e:
            logger.exception("Error obteniendo evento logístico por id")
            raise RepositoryError(f"No se pudo obtener el evento logístico: {e}") from e

    def listar_por_envio(self, id_envio: int) -> list[EventoLogistico]:
        try:
            docs = self._collection.find({"id_envio": id_envio}).sort("fecha_hora", 1)
            return [_doc_to_evento(d) for d in docs]
        except PyMongoError as e:
            logger.exception("Error listando eventos logísticos de un envío")
            raise RepositoryError(f"No se pudo listar los eventos del envío: {e}") from e

    def listar(self, limite: int = 50) -> list[EventoLogistico]:
        try:
            docs = self._collection.find().sort("fecha_hora", -1).limit(limite)
            return [_doc_to_evento(d) for d in docs]
        except PyMongoError as e:
            logger.exception("Error listando eventos logísticos")
            raise RepositoryError(f"No se pudo listar los eventos logísticos: {e}") from e
