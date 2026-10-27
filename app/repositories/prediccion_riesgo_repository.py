"""Acceso a datos de PrediccionRiesgo contra MongoDB (colección
predicciones_riesgo). El alta manual simula el resultado de un proceso de
predicción (pendiente de implementar con scikit-learn, ver context.md)."""
import logging
from datetime import datetime, timezone

from pymongo.errors import PyMongoError

from app.core.exceptions import RepositoryError
from app.db.mongo import get_db
from app.domain.prediccion_riesgo import PrediccionRiesgo

logger = logging.getLogger(__name__)

_COLLECTION = "predicciones_riesgo"


def _doc_to_prediccion(doc: dict) -> PrediccionRiesgo:
    return PrediccionRiesgo(
        id_prediccion=str(doc["_id"]),
        id_envio=doc["id_envio"],
        probabilidad_demora=doc["probabilidad_demora"],
        riesgo_climatico=doc.get("riesgo_climatico", 0.0),
        riesgo_operativo=doc.get("riesgo_operativo", 0.0),
        features_entrada=doc.get("features_entrada", {}),
        fecha_calculo=doc["fecha_calculo"],
    )


class PrediccionRiesgoRepository:
    def __init__(self):
        self._collection = get_db()[_COLLECTION]

    def crear(self, prediccion: PrediccionRiesgo) -> str:
        try:
            doc = {
                "id_envio": prediccion.id_envio,
                "probabilidad_demora": prediccion.probabilidad_demora,
                "riesgo_climatico": prediccion.riesgo_climatico,
                "riesgo_operativo": prediccion.riesgo_operativo,
                "features_entrada": prediccion.features_entrada,
                "fecha_calculo": prediccion.fecha_calculo or datetime.now(timezone.utc),
            }
            result = self._collection.insert_one(doc)
            return str(result.inserted_id)
        except PyMongoError as e:
            logger.exception("Error creando predicción de riesgo")
            raise RepositoryError(f"No se pudo crear la predicción: {e}") from e

    def ultima_por_envio(self, id_envio: int) -> PrediccionRiesgo | None:
        try:
            doc = self._collection.find_one({"id_envio": id_envio}, sort=[("fecha_calculo", -1)])
            return _doc_to_prediccion(doc) if doc else None
        except PyMongoError as e:
            logger.exception("Error obteniendo última predicción de un envío")
            raise RepositoryError(f"No se pudo obtener la predicción: {e}") from e

    def listar_por_envio(self, id_envio: int) -> list[PrediccionRiesgo]:
        try:
            docs = self._collection.find({"id_envio": id_envio}).sort("fecha_calculo", -1)
            return [_doc_to_prediccion(d) for d in docs]
        except PyMongoError as e:
            logger.exception("Error listando predicciones de un envío")
            raise RepositoryError(f"No se pudo listar las predicciones del envío: {e}") from e
