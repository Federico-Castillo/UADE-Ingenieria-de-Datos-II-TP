"""La UI arranca solo en la máquina local salvo que se pida otra cosa (sin servidor real)."""
import pytest

from app.ui import principal


@pytest.fixture(autouse=True)
def limpiar_datos_de_test():
    yield


@pytest.fixture(autouse=True)
def limpiar_mongo_de_test():
    yield


@pytest.fixture(autouse=True)
def limpiar_neo4j_de_test():
    yield


@pytest.fixture
def capturar_arranque(monkeypatch):
    llamadas = {}
    monkeypatch.setattr(principal.ui, "run", lambda **kw: llamadas.update(kw))
    monkeypatch.setattr(principal.app, "add_static_files", lambda *a, **k: None)
    return llamadas


def test_por_defecto_escucha_solo_en_localhost(monkeypatch, capturar_arranque):
    monkeypatch.delenv("UI_HOST", raising=False)
    principal.iniciar()
    assert capturar_arranque["host"] == "127.0.0.1"
    assert capturar_arranque["port"] == 8090


def test_abrirla_a_la_red_requiere_pedirlo_y_avisa(monkeypatch, capturar_arranque, capsys):
    monkeypatch.setenv("UI_HOST", "0.0.0.0")
    principal.iniciar()
    assert capturar_arranque["host"] == "0.0.0.0"
    assert "no tiene autenticación" in capsys.readouterr().out
