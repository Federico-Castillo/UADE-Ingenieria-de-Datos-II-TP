"""Reportes operativos y analíticos (agregaciones de solo lectura, no ABMs,
checklist de promoción). Cada método resuelve una de las agregaciones
pedidas por la consigna uniendo MySQL (Envio/Cliente) con MongoDB (Incidente/
EventoLogistico/PrediccionRiesgo) **a nivel aplicación** — no hay joins
nativos cross-engine, mismo criterio que ya usa LecturaSensorService para
resolver id_envio desde un sensor. No persisten nada: el registro de "se pidió
este reporte" es responsabilidad de Reporte/ReporteService (ver
reporte_menu.py), separado a propósito de este cálculo."""
import logging
from collections import defaultdict

from app.core.fechas import sin_tz
from app.domain.envio import Envio
from app.domain.incidente import Incidente
from app.repositories.cliente_repository import ClienteRepository
from app.repositories.envio_contenedor_repository import EnvioContenedorRepository
from app.repositories.envio_repository import EnvioRepository
from app.repositories.evento_logistico_repository import EventoLogisticoRepository
from app.repositories.incidente_repository import IncidenteRepository
from app.repositories.prediccion_riesgo_repository import PrediccionRiesgoRepository

logger = logging.getLogger(__name__)

_TIPO_EVENTO_ENTREGA = "entregado"
_UMBRAL_RIESGO_ALTO_DEFAULT = 0.6
_SIN_PAIS = "(sin país)"


class ReporteOperativoService:
    def __init__(
        self,
        envio_repo: EnvioRepository | None = None,
        cliente_repo: ClienteRepository | None = None,
        incidente_repo: IncidenteRepository | None = None,
        evento_repo: EventoLogisticoRepository | None = None,
        prediccion_repo: PrediccionRiesgoRepository | None = None,
        envio_contenedor_repo: EnvioContenedorRepository | None = None,
    ):
        self._envio_repo = envio_repo or EnvioRepository()
        self._cliente_repo = cliente_repo or ClienteRepository()
        self._incidente_repo = incidente_repo or IncidenteRepository()
        self._evento_repo = evento_repo or EventoLogisticoRepository()
        self._prediccion_repo = prediccion_repo or PrediccionRiesgoRepository()
        self._envio_contenedor_repo = envio_contenedor_repo or EnvioContenedorRepository()

    def _clientes_por_id(self) -> dict[int, object]:
        return {c.id_cliente: c for c in self._cliente_repo.listar()}

    def _pais_del_envio(self, envio: Envio, clientes_por_id: dict) -> str:
        cliente = clientes_por_id.get(envio.id_cliente)
        return (cliente.pais if cliente else None) or _SIN_PAIS

    # --- Reportes de envíos ---

    def envios_por_pais(self) -> list[dict]:
        clientes_por_id = self._clientes_por_id()
        conteo = defaultdict(int)
        for envio in self._envio_repo.listar():
            conteo[self._pais_del_envio(envio, clientes_por_id)] += 1
        return [{"pais": pais, "cantidad": cantidad} for pais, cantidad in sorted(conteo.items())]

    def envios_por_estado(self) -> list[dict]:
        conteo = defaultdict(int)
        for envio in self._envio_repo.listar():
            conteo[envio.estado] += 1
        return [{"estado": estado, "cantidad": cantidad} for estado, cantidad in sorted(conteo.items())]

    def envios_por_cliente(self) -> list[dict]:
        clientes_por_id = self._clientes_por_id()
        conteo = defaultdict(int)
        for envio in self._envio_repo.listar():
            conteo[envio.id_cliente] += 1
        resultado = [
            {
                "id_cliente": id_cliente,
                "razon_social": clientes_por_id[id_cliente].razon_social
                if id_cliente in clientes_por_id else "(desconocido)",
                "cantidad": cantidad,
            }
            for id_cliente, cantidad in conteo.items()
        ]
        return sorted(resultado, key=lambda r: r["cantidad"], reverse=True)

    def envios_demorados(self) -> list[Envio]:
        return [e for e in self._envio_repo.listar() if e.estado == "demorado"]

    def incidentes_abiertos(self) -> list[Incidente]:
        return self._incidente_repo.listar(solo_abiertos=True)

    # --- Tiempos de entrega ---

    def _duraciones_entrega(self) -> list[dict]:
        """Para cada envío con un evento 'entregado' registrado, la duración
        en horas entre fecha_creacion (MySQL) y la fecha de ese evento
        (Mongo). Un envío sin ese evento no tiene con qué calcularse y queda
        afuera del promedio en vez de contarse como 0."""
        envios_por_id = {e.id_envio: e for e in self._envio_repo.listar()}
        duraciones = []
        for evento in self._evento_repo.listar_por_tipo_evento(_TIPO_EVENTO_ENTREGA):
            envio = envios_por_id.get(evento.id_envio)
            if envio is None or envio.fecha_creacion is None or evento.fecha_hora is None:
                continue
            horas = (sin_tz(evento.fecha_hora) - sin_tz(envio.fecha_creacion)).total_seconds() / 3600
            if horas < 0:
                continue
            duraciones.append({"id_envio": envio.id_envio, "id_cliente": envio.id_cliente, "horas": horas})
        return duraciones

    def tiempos_envio_por_cliente(self) -> list[dict]:
        clientes_por_id = self._clientes_por_id()
        horas_por_cliente = defaultdict(list)
        for d in self._duraciones_entrega():
            horas_por_cliente[d["id_cliente"]].append(d["horas"])
        resultado = [
            {
                "id_cliente": id_cliente,
                "razon_social": clientes_por_id[id_cliente].razon_social
                if id_cliente in clientes_por_id else "(desconocido)",
                "cantidad_envios": len(horas),
                "horas_min": min(horas),
                "horas_max": max(horas),
                "horas_promedio": sum(horas) / len(horas),
            }
            for id_cliente, horas in horas_por_cliente.items()
        ]
        return sorted(resultado, key=lambda r: r["razon_social"])

    def tiempo_promedio_entrega(self) -> dict:
        duraciones = [d["horas"] for d in self._duraciones_entrega()]
        if not duraciones:
            return {"cantidad_envios": 0, "horas_promedio": None}
        return {"cantidad_envios": len(duraciones), "horas_promedio": sum(duraciones) / len(duraciones)}

    # --- Incidentes promedio ---

    def _incidentes_por_envio(self) -> dict[int, int]:
        conteo = defaultdict(int)
        for incidente in self._incidente_repo.listar():
            conteo[incidente.id_envio] += 1
        return conteo

    def _promedio_incidentes_agrupado(self, clave) -> list[dict]:
        incidentes_por_envio = self._incidentes_por_envio()
        envios_por_grupo = defaultdict(int)
        incidentes_por_grupo = defaultdict(int)
        clientes_por_id = self._clientes_por_id()
        for envio in self._envio_repo.listar():
            grupo = clave(envio, clientes_por_id)
            envios_por_grupo[grupo] += 1
            incidentes_por_grupo[grupo] += incidentes_por_envio.get(envio.id_envio, 0)
        return [
            {
                "grupo": grupo,
                "cantidad_envios": envios_por_grupo[grupo],
                "cantidad_incidentes": incidentes_por_grupo[grupo],
                "promedio_por_envio": incidentes_por_grupo[grupo] / envios_por_grupo[grupo],
            }
            for grupo in sorted(envios_por_grupo, key=str)
        ]

    def incidentes_promedio_por_pais(self) -> list[dict]:
        return self._promedio_incidentes_agrupado(self._pais_del_envio)

    def incidentes_promedio_por_estado(self) -> list[dict]:
        return self._promedio_incidentes_agrupado(lambda envio, _: envio.estado)

    def incidentes_promedio_por_cliente(self) -> list[dict]:
        resultado = self._promedio_incidentes_agrupado(lambda envio, _: envio.id_cliente)
        clientes_por_id = self._clientes_por_id()
        for fila in resultado:
            cliente = clientes_por_id.get(fila["grupo"])
            fila["razon_social"] = cliente.razon_social if cliente else "(desconocido)"
        return resultado

    # --- Análisis predictivo (atrasos y riesgos) ---

    def _ultima_prediccion_por_envio(self) -> list:
        vistos = set()
        ultimas = []
        for prediccion in self._prediccion_repo.listar_todas():
            if prediccion.id_envio in vistos:
                continue
            vistos.add(prediccion.id_envio)
            ultimas.append(prediccion)
        return ultimas

    def analisis_predictivo_riesgos(self, umbral_riesgo: float = _UMBRAL_RIESGO_ALTO_DEFAULT) -> dict:
        predicciones = self._ultima_prediccion_por_envio()
        if not predicciones:
            return {"cantidad_envios": 0, "probabilidad_demora_promedio": None, "envios_riesgo_alto": []}
        promedio = sum(p.probabilidad_demora for p in predicciones) / len(predicciones)
        riesgo_alto = sorted(
            (p for p in predicciones if p.probabilidad_demora >= umbral_riesgo),
            key=lambda p: p.probabilidad_demora,
            reverse=True,
        )
        return {
            "cantidad_envios": len(predicciones),
            "probabilidad_demora_promedio": promedio,
            "envios_riesgo_alto": [
                {
                    "id_envio": p.id_envio,
                    "probabilidad_demora": p.probabilidad_demora,
                    "riesgo_climatico": p.riesgo_climatico,
                    "riesgo_operativo": p.riesgo_operativo,
                }
                for p in riesgo_alto
            ],
        }

    # --- Rankings ---

    def ranking_rutas_por_incidentes(self, top_n: int = 10) -> list[dict]:
        """"Ruta" = el par (origen, destino) declarado en el envío (no el
        tramo: un envío puede tener varios tramos y un incidente no apunta a
        uno en particular, solo al envío). Solo incluye rutas con al menos
        un incidente — es un ranking de rutas problemáticas, no un listado
        completo."""
        incidentes_por_envio = self._incidentes_por_envio()
        envios_por_ruta = defaultdict(int)
        incidentes_por_ruta = defaultdict(int)
        for envio in self._envio_repo.listar():
            ruta = (envio.origen, envio.destino)
            envios_por_ruta[ruta] += 1
            incidentes_por_ruta[ruta] += incidentes_por_envio.get(envio.id_envio, 0)

        filas = [
            {
                "origen": origen,
                "destino": destino,
                "cantidad_incidentes": incidentes_por_ruta[(origen, destino)],
                "cantidad_envios": envios_por_ruta[(origen, destino)],
            }
            for origen, destino in envios_por_ruta
            if incidentes_por_ruta[(origen, destino)] > 0
        ]
        filas.sort(key=lambda f: f["cantidad_incidentes"], reverse=True)
        return filas[:top_n]

    def ranking_clientes_por_volumen(self, top_n: int = 10) -> list[dict]:
        """"Volumen transportado" = suma de Contenedor.capacidad de todos los
        contenedores que el cliente movió (vía envio_contenedor), no la
        cantidad de envíos — eso ya lo cubre envios_por_cliente()."""
        clientes_por_id = self._clientes_por_id()
        filas = self._envio_contenedor_repo.volumen_transportado_por_cliente()
        resultado = [
            {
                "id_cliente": f["id_cliente"],
                "razon_social": clientes_por_id[f["id_cliente"]].razon_social
                if f["id_cliente"] in clientes_por_id else "(desconocido)",
                "volumen_total": f["volumen_total"],
                "cantidad_contenedores": f["cantidad_contenedores"],
            }
            for f in filas
        ]
        return resultado[:top_n]
