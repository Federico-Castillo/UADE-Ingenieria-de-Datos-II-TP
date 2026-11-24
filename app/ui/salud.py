"""Estado de los 5 motores. Dos niveles:

  * `verificar_todos`: chequeo real (login/ping) con timeout, para el arranque.
  * `estado_rapido`: solo abre el puerto TCP; es barato y alcanza para el
    indicador en vivo del encabezado y para ver que un motor se cayó.

Usa conexiones propias y de vida corta (no toca los singletons de app/db),
así un motor caído no cuelga ni envenena las conexiones de la aplicación.
No importa NiceGUI."""
import socket
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

from app.config import get_config

MOTORES = ["MySQL", "MongoDB", "Neo4j", "Redis", "Cassandra"]


def _host_port(motor: str) -> tuple[str, int]:
    c = get_config()
    if motor == "MySQL":
        return c.mysql.host, c.mysql.port
    if motor == "MongoDB":
        return c.mongo.host, c.mongo.port
    if motor == "Redis":
        return c.redis.host, c.redis.port
    if motor == "Cassandra":
        return c.cassandra.hosts[0], c.cassandra.port
    u = urlparse(c.neo4j.uri)
    return u.hostname or "localhost", u.port or 7687


def puerto_abierto(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def estado_rapido(timeout: float = 1.0) -> dict[str, bool]:
    with ThreadPoolExecutor(max_workers=len(MOTORES)) as pool:
        futuros = {m: pool.submit(puerto_abierto, *_host_port(m), timeout) for m in MOTORES}
        return {m: f.result() for m, f in futuros.items()}


def _chequear(motor: str, timeout: float) -> None:
    """Levanta una excepción si el motor no responde."""
    c = get_config()
    if motor == "MySQL":
        import mysql.connector
        conn = mysql.connector.connect(
            host=c.mysql.host, port=c.mysql.port, user=c.mysql.user, password=c.mysql.password,
            database=c.mysql.database, connection_timeout=int(timeout),
        )
        conn.close()
    elif motor == "MongoDB":
        from pymongo import MongoClient
        cliente = MongoClient(host=c.mongo.host, port=c.mongo.port, serverSelectionTimeoutMS=int(timeout * 1000))
        try:
            cliente.admin.command("ping")
        finally:
            cliente.close()
    elif motor == "Redis":
        import redis
        r = redis.Redis(host=c.redis.host, port=c.redis.port, db=c.redis.db,
                        socket_connect_timeout=timeout, socket_timeout=timeout)
        try:
            r.ping()
        finally:
            r.close()
    elif motor == "Neo4j":
        from neo4j import GraphDatabase
        drv = GraphDatabase.driver(c.neo4j.uri, auth=(c.neo4j.user, c.neo4j.password),
                                   connection_timeout=timeout, max_transaction_retry_time=0)
        try:
            drv.verify_connectivity()
        finally:
            drv.close()
    else:  # Cassandra
        import app.db._cassandra_compat  # noqa: F401 (shim de asyncore, ver app/db/cassandra_client.py)
        from cassandra.cluster import Cluster
        from cassandra.io.asyncioreactor import AsyncioConnection
        cluster = Cluster(contact_points=c.cassandra.hosts, port=c.cassandra.port,
                          connection_class=AsyncioConnection, connect_timeout=timeout)
        try:
            cluster.connect().shutdown()
        finally:
            cluster.shutdown()


def verificar_todos(timeout: float = 4.0) -> dict[str, tuple[bool, str]]:
    """{motor: (ok, detalle)}; los chequeos corren en paralelo."""
    def uno(motor: str) -> tuple[bool, str]:
        try:
            _chequear(motor, timeout)
            return True, "OK"
        except Exception as e:  # cualquier fallo de driver significa "no disponible"
            return False, f"{type(e).__name__}: {str(e).splitlines()[0][:120] if str(e) else ''}".rstrip(": ")

    pool = ThreadPoolExecutor(max_workers=len(MOTORES))
    try:
        futuros = {m: pool.submit(uno, m) for m in MOTORES}
        return {m: f.result() for m, f in futuros.items()}
    finally:
        pool.shutdown(wait=False)
