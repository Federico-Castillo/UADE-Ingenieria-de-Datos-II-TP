"""Carga la configuración de la aplicación desde variables de entorno (.env)."""
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv

from app.core.exceptions import ConnectionConfigError

load_dotenv()


def _require(name: str) -> str:
    value = os.getenv(name)
    if value is None or value == "":
        raise ConnectionConfigError(
            f"Falta la variable de entorno obligatoria '{name}'. "
            f"Revisá tu archivo .env (ver .env.example)."
        )
    return value


@dataclass(frozen=True)
class MySQLConfig:
    host: str
    port: int
    user: str
    password: str
    database: str


@dataclass(frozen=True)
class MongoConfig:
    host: str
    port: int
    database: str


@dataclass(frozen=True)
class Neo4jConfig:
    uri: str
    user: str
    password: str


@dataclass(frozen=True)
class RedisConfig:
    host: str
    port: int
    db: int


@dataclass(frozen=True)
class CassandraConfig:
    hosts: list[str]
    port: int
    keyspace: str


@dataclass(frozen=True)
class AppConfig:
    mysql: MySQLConfig
    mongo: MongoConfig
    neo4j: Neo4jConfig
    redis: RedisConfig
    cassandra: CassandraConfig
    log_level: str
    log_file: str


@lru_cache
def get_config() -> AppConfig:
    mysql = MySQLConfig(
        host=_require("MYSQL_HOST"),
        port=int(_require("MYSQL_PORT")),
        user=_require("MYSQL_USER"),
        password=_require("MYSQL_PASSWORD"),
        database=_require("MYSQL_DATABASE"),
    )
    mongo = MongoConfig(
        host=_require("MONGO_HOST"),
        port=int(_require("MONGO_PORT")),
        database=_require("MONGO_DATABASE"),
    )
    neo4j = Neo4jConfig(
        uri=_require("NEO4J_URI"),
        user=_require("NEO4J_USER"),
        password=_require("NEO4J_PASSWORD"),
    )
    redis = RedisConfig(
        host=_require("REDIS_HOST"),
        port=int(_require("REDIS_PORT")),
        db=int(_require("REDIS_DB")),
    )
    cassandra = CassandraConfig(
        hosts=[h.strip() for h in _require("CASSANDRA_HOSTS").split(",")],
        port=int(_require("CASSANDRA_PORT")),
        keyspace=_require("CASSANDRA_KEYSPACE"),
    )
    return AppConfig(
        mysql=mysql,
        mongo=mongo,
        neo4j=neo4j,
        redis=redis,
        cassandra=cassandra,
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        log_file=os.getenv("LOG_FILE", "logs/app.log"),
    )
