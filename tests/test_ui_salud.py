"""Chequeos de puerto de app/ui/salud.py (sin motores reales: usa sockets locales)."""
import socket

import pytest

from app.ui import salud


@pytest.fixture(autouse=True)
def limpiar_datos_de_test():
    yield


@pytest.fixture(autouse=True)
def limpiar_mongo_de_test():
    yield


@pytest.fixture(autouse=True)
def limpiar_neo4j_de_test():
    yield


def test_puerto_abierto_y_cerrado():
    with socket.socket() as srv:
        srv.bind(("127.0.0.1", 0))
        srv.listen(1)
        puerto = srv.getsockname()[1]
        assert salud.puerto_abierto("127.0.0.1", puerto, timeout=1.0)
    # al cerrar el socket el puerto deja de aceptar conexiones
    assert not salud.puerto_abierto("127.0.0.1", puerto, timeout=0.5)


def test_estado_rapido_refleja_cada_motor(monkeypatch):
    puertos = {m: 1000 + i for i, m in enumerate(salud.MOTORES)}
    monkeypatch.setattr(salud, "_host_port", lambda motor: ("h", puertos[motor]))
    monkeypatch.setattr(salud, "puerto_abierto", lambda host, port, timeout=1.0: port != puertos["Redis"])
    estado = salud.estado_rapido()
    assert set(estado) == set(salud.MOTORES)
    assert estado["Redis"] is False
    assert all(estado[m] for m in salud.MOTORES if m != "Redis")
