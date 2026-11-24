"""Opciones de ECharts (series tipo `graph`) para visualizar lo que vive en
Neo4j. Funciones puras sobre las filas que devuelve TramoService, así que se
testean sin NiceGUI ni Neo4j."""

_CATEGORIAS_RED = [{"name": "Cliente"}, {"name": "Operador logístico"}]


def opciones_red(filas: list[dict]) -> dict:
    """Red cliente <-> operador: dos clientes que comparten operador quedan
    unidos por él. `filas` es TramoService.red_relaciones()."""
    nodos: dict[str, dict] = {}
    enlaces: set[tuple[str, str]] = set()
    grado: dict[str, int] = {}
    for f in filas:
        c, o = f"c{f['id_cliente']}", f"o{f['id_operador_logistico']}"
        nodos.setdefault(c, {"id": c, "name": f["cliente"], "category": 0})
        nodos.setdefault(o, {"id": o, "name": f["operador"], "category": 1})
        if (c, o) not in enlaces:
            enlaces.add((c, o))
            grado[c] = grado.get(c, 0) + 1
            grado[o] = grado.get(o, 0) + 1
    for id_nodo, n in nodos.items():
        n["symbolSize"] = 22 + 6 * grado.get(id_nodo, 0)
    return {
        "title": {"text": "Red de clientes y operadores logísticos"},
        "tooltip": {},
        "legend": [{"data": [c["name"] for c in _CATEGORIAS_RED], "top": 24}],
        "series": [{
            "type": "graph", "layout": "force", "roam": True, "draggable": True,
            "data": list(nodos.values()),
            "links": [{"source": a, "target": b} for a, b in sorted(enlaces)],
            "categories": _CATEGORIAS_RED,
            "label": {"show": True, "position": "right"},
            "force": {"repulsion": 320, "edgeLength": 130},
            "emphasis": {"focus": "adjacency"},
        }],
    }


def opciones_ruta(tramos: list[dict], id_envio) -> dict:
    """Ruta de un envío como cadena de ubicaciones; cada arista es un tramo
    etiquetado con medio de transporte y vehículo. `tramos` es
    TramoService.ruta_completa() (ya viene ordenada por `orden`)."""
    ordenados = sorted(tramos, key=lambda t: (t.get("orden") is None, t.get("orden") or 0))
    nodos, enlaces = [], []
    if ordenados:
        nodos.append({"id": "n0", "name": ordenados[0]["origen"]})
    for i, t in enumerate(ordenados):
        nodos.append({"id": f"n{i + 1}", "name": t["destino"]})
        enlaces.append({
            "source": f"n{i}", "target": f"n{i + 1}",
            "value": f"{t['medio_transporte']} · {t.get('vehiculo') or 's/vehículo'}",
            "label": {"show": True, "formatter": f"{t['medio_transporte']} · {t.get('vehiculo') or 's/vehículo'}"},
        })
    for i, n in enumerate(nodos):
        n.update({"x": i * 220, "y": 0, "symbolSize": 34})
    return {
        "title": {"text": f"Ruta del envío {id_envio}"},
        "tooltip": {},
        "series": [{
            "type": "graph", "layout": "none", "roam": True,
            "data": nodos, "links": enlaces,
            "edgeSymbol": ["none", "arrow"], "edgeSymbolSize": 10,
            "label": {"show": True, "position": "bottom"},
            "lineStyle": {"width": 3, "curveness": 0.15},
        }],
    }
