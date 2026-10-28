"""Acceso a datos de Incidente contra MongoDB (colección incidentes)."""
import logging
from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from pymongo.errors import PyMongoError

from app.core.exceptions import RepositoryError
from app.db.mongo import get_db
from app.domain.incidente import Incidente

logger = logging.getLogger(__name__)

_COLLECTION = "incidentes"


def _doc_to_incidente(doc: dict) -> Incidente:
    return Incidente(
        id_incidente=str(doc["_id"]),
        id_envio=doc["id_envio"],
        tipo=doc["tipo"],
        severidad=doc["severidad"],
        descripcion=doc.get("descripcion", ""),
        estado=doc["estado"],
        fecha=doc["fecha"],
    )


class IncidenteRepository:
    def __init__(self):
        self._collection = get_db()[_COLLECTION]

    def crear(self, incidente: Incidente) -> str:
        try:
            doc = {
                "id_envio": incidente.id_envio,
                "tipo": incidente.tipo,
                "severidad": incidente.severidad,
                "descripcion": incidente.descripcion,
                "estado": incidente.estado,
                "fecha": incidente.fecha or datetime.now(timezone.utc),
            }
            result = self._collection.insert_one(doc)
            id_incidente = str(result.inserted_id)
            logger.info("Incidente creado id=%s id_envio=%s tipo=%s severidad=%s", id_incidente, incidente.id_envio, incidente.tipo, incidente.severidad)
            return id_incidente
        except PyMongoError as e:
            logger.exception("Error creando incidente")
            raise RepositoryError(f"No se pudo crear el incidente: {e}") from e

    def obtener_por_id(self, id_incidente: str) -> Incidente | None:
        try:
            doc = self._collection.find_one({"_id": ObjectId(id_incidente)})
            return _doc_to_incidente(doc) if doc else None
        except InvalidId:
            return None
        except PyMongoError as e:
            logger.exception("Error obteniendo incidente por id")
            raise RepositoryError(f"No se pudo obtener el incidente: {e}") from e

    def listar_por_envio(self, id_envio: int) -> list[Incidente]:
        try:
            docs = self._collection.find({"id_envio": id_envio}).sort("fecha", 1)
            return [_doc_to_incidente(d) for d in docs]
        except PyMongoError as e:
            logger.exception("Error listando incidentes de un envío")
            raise RepositoryError(f"No se pudo listar los incidentes del envío: {e}") from e

    def listar(self, solo_abiertos: bool = False) -> list[Incidente]:
        try:
            filtro = {"estado": "abierto"} if solo_abiertos else {}
            docs = self._collection.find(filtro).sort("fecha", -1)
            return [_doc_to_incidente(d) for d in docs]
        except PyMongoError as e:
            logger.exception("Error listando incidentes")
            raise RepositoryError(f"No se pudo listar los incidentes: {e}") from e

    def actualizar_estado(self, id_incidente: str, estado: str) -> bool:
        try:
            result = self._collection.update_one(
                {"_id": ObjectId(id_incidente)}, {"$set": {"estado": estado}}
            )
            actualizado = result.matched_count > 0
            if actualizado:
                logger.info("Incidente actualizado id=%s nuevo_estado=%s", id_incidente, estado)
            return actualizado
        except InvalidId:
            return False
        except PyMongoError as e:
            logger.exception("Error actualizando estado de incidente")
            raise RepositoryError(f"No se pudo actualizar el incidente: {e}") from e
