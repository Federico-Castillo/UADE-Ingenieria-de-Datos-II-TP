"""Shim de compatibilidad: cassandra-driver (hasta 3.30.x) auto-selecciona su
connection_class por defecto probando gevent/eventlet/libev/asyncore, sin
fallback a asyncio — y `asyncore` fue removido del stdlib en Python 3.12, lo
que rompe el import de `cassandra.cluster` incluso antes de poder pasar
connection_class=AsyncioConnection explícitamente (que es lo que usamos,
ver app/db/cassandra_client.py). Este stub solo necesita existir para que la
definición de clases en cassandra.io.asyncorereactor no falle al importar —
nunca se usa en tiempo de ejecución porque forzamos AsyncioConnection."""
import sys
import types

if "asyncore" not in sys.modules:
    _stub = types.ModuleType("asyncore")

    class _Dispatcher:
        def __init__(self, *args, **kwargs):
            pass

        def close(self):
            pass

    _stub.dispatcher = _Dispatcher
    _stub.loop = lambda *args, **kwargs: None
    sys.modules["asyncore"] = _stub
