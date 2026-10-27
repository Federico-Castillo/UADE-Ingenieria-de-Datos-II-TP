"""Crea las 5 colecciones de MongoDB con sus validadores $jsonSchema e índices,
transcripción fiel de "2. modelado.md" / Punto 2 — MongoDB — Documental.
Idempotente: si la colección ya existe, actualiza el validador con collMod."""
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from pymongo.errors import PyMongoError

from app.db.mongo import get_db

logger = logging.getLogger(__name__)

COLLECTIONS = {
    "eventos_logisticos": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["id_envio", "fecha_hora", "tipo_evento"],
            "properties": {
                "id_envio": {"bsonType": "int"},
                "fecha_hora": {"bsonType": "date"},
                "tipo_evento": {"bsonType": "string"},
                "ubicacion": {"bsonType": "object"},
                "descripcion": {"bsonType": "string"},
            },
        }
    },
    "incidentes": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["id_envio", "tipo", "fecha", "severidad", "estado"],
            "properties": {
                "id_envio": {"bsonType": "int"},
                "tipo": {"bsonType": "string"},
                "fecha": {"bsonType": "date"},
                "severidad": {"enum": ["baja", "media", "alta", "critica"]},
                "estado": {"enum": ["abierto", "en_revision", "cerrado"]},
                "descripcion": {"bsonType": "string"},
            },
        }
    },
    "mensajes": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["id_remitente", "fecha_hora", "contenido", "tipo"],
            "properties": {
                "id_remitente": {"bsonType": "int"},
                "id_destinatario": {"bsonType": ["int", "null"]},
                "id_grupo": {"bsonType": ["objectId", "null"]},
                "fecha_hora": {"bsonType": "date"},
                "contenido": {"bsonType": "string"},
                "tipo": {"enum": ["privado", "grupal"]},
            },
        }
    },
    "grupos_trabajo": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["nombre", "integrantes"],
            "properties": {
                "nombre": {"bsonType": "string"},
                "integrantes": {"bsonType": "array", "items": {"bsonType": "int"}},
            },
        }
    },
    "predicciones_riesgo": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["id_envio", "probabilidad_demora", "fecha_calculo"],
            "properties": {
                "id_envio": {"bsonType": "int"},
                "probabilidad_demora": {"bsonType": "double"},
                "riesgo_climatico": {"bsonType": "double"},
                "riesgo_operativo": {"bsonType": "double"},
                "fecha_calculo": {"bsonType": "date"},
                "features_entrada": {"bsonType": "object"},
            },
        }
    },
}

INDEXES = {
    "eventos_logisticos": [
        ([("id_envio", 1), ("fecha_hora", 1)], {}),
        ([("tipo_evento", 1)], {}),
    ],
    "incidentes": [
        ([("id_envio", 1)], {}),
        ([("estado", 1)], {}),
        ([("tipo", 1), ("severidad", 1)], {}),
    ],
    "mensajes": [
        ([("id_remitente", 1), ("id_destinatario", 1), ("fecha_hora", 1)], {}),
        ([("id_grupo", 1), ("fecha_hora", 1)], {}),
    ],
    "grupos_trabajo": [
        ([("integrantes", 1)], {}),
    ],
    "predicciones_riesgo": [
        ([("id_envio", 1), ("fecha_calculo", -1)], {}),
    ],
}


def create_schema() -> None:
    db = get_db()
    existing = set(db.list_collection_names())

    for name, validator in COLLECTIONS.items():
        if name in existing:
            db.command("collMod", name, validator=validator)
            logger.info("Colección '%s' ya existía, validador actualizado", name)
        else:
            db.create_collection(name, validator=validator)
            logger.info("Colección '%s' creada", name)

        for keys, opts in INDEXES[name]:
            db[name].create_index(keys, **opts)

    logger.info("Esquema de MongoDB listo (%s colecciones)", len(COLLECTIONS))


if __name__ == "__main__":
    from app.logging_config import setup_logging

    setup_logging()
    try:
        create_schema()
        print("MongoDB: OK")
    except PyMongoError as e:
        print(f"MongoDB: ERROR ({e})")
        raise
