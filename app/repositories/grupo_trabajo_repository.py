"""Acceso a datos de GrupoTrabajo contra MongoDB (colección grupos_trabajo)."""
import logging

from bson import ObjectId
from bson.errors import InvalidId
from pymongo.errors import PyMongoError

from app.core.exceptions import RepositoryError
from app.db.mongo import get_db
from app.domain.grupo_trabajo import GrupoTrabajo

logger = logging.getLogger(__name__)

_COLLECTION = "grupos_trabajo"


def _doc_to_grupo(doc: dict) -> GrupoTrabajo:
    return GrupoTrabajo(
        id_grupo=str(doc["_id"]),
        nombre=doc["nombre"],
        integrantes=doc.get("integrantes", []),
    )


class GrupoTrabajoRepository:
    def __init__(self):
        self._collection = get_db()[_COLLECTION]

    def crear(self, grupo: GrupoTrabajo) -> str:
        try:
            doc = {"nombre": grupo.nombre, "integrantes": grupo.integrantes}
            result = self._collection.insert_one(doc)
            id_grupo = str(result.inserted_id)
            logger.info("Grupo de trabajo creado id=%s nombre=%s", id_grupo, grupo.nombre)
            return id_grupo
        except PyMongoError as e:
            logger.exception("Error creando grupo de trabajo")
            raise RepositoryError(f"No se pudo crear el grupo de trabajo: {e}") from e

    def obtener_por_id(self, id_grupo: str) -> GrupoTrabajo | None:
        try:
            doc = self._collection.find_one({"_id": ObjectId(id_grupo)})
            return _doc_to_grupo(doc) if doc else None
        except InvalidId:
            return None
        except PyMongoError as e:
            logger.exception("Error obteniendo grupo de trabajo por id")
            raise RepositoryError(f"No se pudo obtener el grupo de trabajo: {e}") from e

    def listar(self) -> list[GrupoTrabajo]:
        try:
            docs = self._collection.find().sort("nombre", 1)
            return [_doc_to_grupo(d) for d in docs]
        except PyMongoError as e:
            logger.exception("Error listando grupos de trabajo")
            raise RepositoryError(f"No se pudo listar los grupos de trabajo: {e}") from e

    def agregar_integrante(self, id_grupo: str, id_usuario: int) -> bool:
        try:
            result = self._collection.update_one(
                {"_id": ObjectId(id_grupo)}, {"$addToSet": {"integrantes": id_usuario}}
            )
            agregado = result.matched_count > 0
            if agregado:
                logger.info("Integrante agregado a grupo de trabajo id_grupo=%s id_usuario=%s", id_grupo, id_usuario)
            return agregado
        except InvalidId:
            return False
        except PyMongoError as e:
            logger.exception("Error agregando integrante a grupo de trabajo")
            raise RepositoryError(f"No se pudo agregar el integrante: {e}") from e

    def quitar_integrante(self, id_grupo: str, id_usuario: int) -> bool:
        try:
            result = self._collection.update_one(
                {"_id": ObjectId(id_grupo)}, {"$pull": {"integrantes": id_usuario}}
            )
            quitado = result.matched_count > 0
            if quitado:
                logger.info("Integrante quitado de grupo de trabajo id_grupo=%s id_usuario=%s", id_grupo, id_usuario)
            return quitado
        except InvalidId:
            return False
        except PyMongoError as e:
            logger.exception("Error quitando integrante de grupo de trabajo")
            raise RepositoryError(f"No se pudo quitar el integrante: {e}") from e

    def eliminar(self, id_grupo: str) -> bool:
        try:
            result = self._collection.delete_one({"_id": ObjectId(id_grupo)})
            eliminado = result.deleted_count > 0
            if eliminado:
                logger.info("Grupo de trabajo eliminado id=%s", id_grupo)
            return eliminado
        except InvalidId:
            return False
        except PyMongoError as e:
            logger.exception("Error eliminando grupo de trabajo")
            raise RepositoryError(f"No se pudo eliminar el grupo de trabajo: {e}") from e
