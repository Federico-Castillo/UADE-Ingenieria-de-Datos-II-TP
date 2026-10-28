"""Acceso a datos de Mensaje contra MongoDB (colección mensajes)."""
import logging
from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from pymongo.errors import PyMongoError

from app.core.exceptions import RepositoryError
from app.db.mongo import get_db
from app.domain.mensaje import Mensaje

logger = logging.getLogger(__name__)

_COLLECTION = "mensajes"


def _doc_to_mensaje(doc: dict) -> Mensaje:
    return Mensaje(
        id_mensaje=str(doc["_id"]),
        id_remitente=doc["id_remitente"],
        id_destinatario=doc.get("id_destinatario"),
        id_grupo=str(doc["id_grupo"]) if doc.get("id_grupo") else None,
        contenido=doc["contenido"],
        tipo=doc["tipo"],
        fecha_hora=doc["fecha_hora"],
    )


class MensajeRepository:
    def __init__(self):
        self._collection = get_db()[_COLLECTION]

    def crear(self, mensaje: Mensaje) -> str:
        try:
            doc = {
                "id_remitente": mensaje.id_remitente,
                "id_destinatario": mensaje.id_destinatario,
                "id_grupo": ObjectId(mensaje.id_grupo) if mensaje.id_grupo else None,
                "contenido": mensaje.contenido,
                "tipo": mensaje.tipo,
                "fecha_hora": mensaje.fecha_hora or datetime.now(timezone.utc),
            }
            result = self._collection.insert_one(doc)
            id_mensaje = str(result.inserted_id)
            logger.info("Mensaje creado id=%s id_remitente=%s tipo=%s", id_mensaje, mensaje.id_remitente, mensaje.tipo)
            return id_mensaje
        except PyMongoError as e:
            logger.exception("Error creando mensaje")
            raise RepositoryError(f"No se pudo crear el mensaje: {e}") from e

    def listar_conversacion_privada(self, id_usuario_a: int, id_usuario_b: int) -> list[Mensaje]:
        try:
            docs = self._collection.find(
                {
                    "tipo": "privado",
                    "$or": [
                        {"id_remitente": id_usuario_a, "id_destinatario": id_usuario_b},
                        {"id_remitente": id_usuario_b, "id_destinatario": id_usuario_a},
                    ],
                }
            ).sort("fecha_hora", 1)
            return [_doc_to_mensaje(d) for d in docs]
        except PyMongoError as e:
            logger.exception("Error listando conversación privada")
            raise RepositoryError(f"No se pudo listar la conversación: {e}") from e

    def listar_de_grupo(self, id_grupo: str) -> list[Mensaje]:
        try:
            docs = self._collection.find({"id_grupo": ObjectId(id_grupo)}).sort("fecha_hora", 1)
            return [_doc_to_mensaje(d) for d in docs]
        except InvalidId:
            return []
        except PyMongoError as e:
            logger.exception("Error listando mensajes de un grupo")
            raise RepositoryError(f"No se pudo listar los mensajes del grupo: {e}") from e
