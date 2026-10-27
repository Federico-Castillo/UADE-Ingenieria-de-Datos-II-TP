"""Predicción real de atrasos con scikit-learn (checklist de Analítica /
predicción): entrena un clasificador sobre los envíos con resultado conocido
('entregado'/'demorado') y predice la probabilidad de demora de los envíos
todavía no resueltos ('pendiente'/'en_transito'), persistiendo el resultado
en PrediccionRiesgo (Mongo) — reemplaza la carga manual por un cálculo real.

Features (todas conocidas ANTES de que el envío se resuelva, para no
entrenar con fuga de información del propio resultado):
- prioridad del envío (ordinal)
- medio de transporte del primer tramo asignado (categórico; 'sin_tramo' si
  todavía no tiene uno)
- tasa histórica de demora del cliente (sobre SUS OTROS envíos resueltos,
  nunca sobre el propio) — si el cliente no tiene otros envíos resueltos, se
  usa la tasa global como prior
- cantidad de envíos previos del cliente (señal de volumen/experiencia)

riesgo_climatico/riesgo_operativo NO son salida del modelo de ML (el
checklist solo pide predicción de atrasos): se completan con una heurística
simple sobre el historial de incidentes del cliente, separando los
disparados por sensores de temperatura/humedad (clima) del resto
(operativo), para no dejarlos en 0 sin ningún criterio."""
import logging
from collections import defaultdict

from sklearn.feature_extraction import DictVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from app.core.exceptions import ValidationError
from app.domain.prediccion_riesgo import PrediccionRiesgo
from app.repositories.envio_repository import EnvioRepository
from app.repositories.incidente_repository import IncidenteRepository
from app.repositories.tramo_repository import TramoRepository
from app.services.prediccion_riesgo_service import PrediccionRiesgoService

logger = logging.getLogger(__name__)

_PRIORIDAD_ORDINAL = {"baja": 0, "normal": 1, "alta": 2, "urgente": 3}
_ESTADOS_RESUELTOS = {"entregado", "demorado"}
_ESTADOS_A_PREDECIR = {"pendiente", "en_transito"}
_MINIMO_MUESTRAS_ENTRENAMIENTO = 4
_TIPOS_INCIDENTE_CLIMA = ("anomalia_temperatura", "anomalia_humedad")


class PrediccionMLService:
    def __init__(
        self,
        envio_repo: EnvioRepository | None = None,
        incidente_repo: IncidenteRepository | None = None,
        tramo_repo: TramoRepository | None = None,
        prediccion_service: PrediccionRiesgoService | None = None,
    ):
        self._envio_repo = envio_repo or EnvioRepository()
        self._incidente_repo = incidente_repo or IncidenteRepository()
        self._tramo_repo = tramo_repo or TramoRepository()
        self._prediccion_service = prediccion_service or PrediccionRiesgoService()

    def _construir_contexto(self):
        envios = self._envio_repo.listar()
        medio_por_envio = self._tramo_repo.medio_transporte_principal_por_envio()
        envios_por_id = {e.id_envio: e for e in envios}
        envios_por_cliente = defaultdict(list)
        for envio in envios:
            envios_por_cliente[envio.id_cliente].append(envio)

        incidentes_clima_por_cliente = defaultdict(int)
        incidentes_total_por_cliente = defaultdict(int)
        for incidente in self._incidente_repo.listar():
            envio = envios_por_id.get(incidente.id_envio)
            if envio is None:
                continue
            incidentes_total_por_cliente[envio.id_cliente] += 1
            if incidente.tipo.startswith(_TIPOS_INCIDENTE_CLIMA):
                incidentes_clima_por_cliente[envio.id_cliente] += 1

        return envios, medio_por_envio, envios_por_cliente, incidentes_total_por_cliente, incidentes_clima_por_cliente

    def _tasa_demora_cliente(self, id_cliente: int, id_envio_excluir: int, envios_por_cliente: dict, tasa_global: float) -> float:
        resueltos = [
            e for e in envios_por_cliente[id_cliente]
            if e.id_envio != id_envio_excluir and e.estado in _ESTADOS_RESUELTOS
        ]
        if not resueltos:
            return tasa_global
        demorados = sum(1 for e in resueltos if e.estado == "demorado")
        return demorados / len(resueltos)

    def _features_envio(self, envio, medio_por_envio: dict, envios_por_cliente: dict, tasa_global: float) -> dict:
        return {
            "prioridad": _PRIORIDAD_ORDINAL.get(envio.prioridad, 1),
            "medio_transporte": medio_por_envio.get(envio.id_envio) or "sin_tramo",
            "tasa_demora_historica_cliente": self._tasa_demora_cliente(
                envio.id_cliente, envio.id_envio, envios_por_cliente, tasa_global
            ),
            "cantidad_envios_previos_cliente": len(envios_por_cliente[envio.id_cliente]) - 1,
        }

    def calcular_predicciones(self) -> list[PrediccionRiesgo]:
        envios, medio_por_envio, envios_por_cliente, incidentes_total, incidentes_clima = self._construir_contexto()

        resueltos = [e for e in envios if e.estado in _ESTADOS_RESUELTOS]
        if len(resueltos) < _MINIMO_MUESTRAS_ENTRENAMIENTO:
            raise ValidationError(
                f"No hay suficientes envíos con resultado conocido para entrenar el modelo "
                f"(hay {len(resueltos)}, se necesitan al menos {_MINIMO_MUESTRAS_ENTRENAMIENTO})."
            )
        if len({e.estado for e in resueltos}) < 2:
            raise ValidationError(
                "Todos los envíos resueltos terminaron con el mismo estado (todos demorados o "
                "ninguno) — no se puede entrenar un clasificador con una sola clase."
            )

        tasa_global = sum(1 for e in resueltos if e.estado == "demorado") / len(resueltos)

        X_train = [self._features_envio(e, medio_por_envio, envios_por_cliente, tasa_global) for e in resueltos]
        y_train = [1 if e.estado == "demorado" else 0 for e in resueltos]

        modelo = Pipeline([
            ("vectorizar", DictVectorizer(sparse=False)),
            ("clasificar", LogisticRegression(class_weight="balanced", max_iter=1000)),
        ])
        modelo.fit(X_train, y_train)

        a_predecir = [e for e in envios if e.estado in _ESTADOS_A_PREDECIR]
        if not a_predecir:
            logger.info("No hay envíos pendientes/en tránsito para predecir.")
            return []

        X_predecir = [self._features_envio(e, medio_por_envio, envios_por_cliente, tasa_global) for e in a_predecir]
        probabilidades = modelo.predict_proba(X_predecir)[:, 1]

        resultado = []
        for envio, probabilidad, features in zip(a_predecir, probabilidades, X_predecir):
            total = incidentes_total.get(envio.id_cliente, 0)
            clima = incidentes_clima.get(envio.id_cliente, 0)
            riesgo_climatico = (clima / total) if total else 0.0
            riesgo_operativo = (1.0 - riesgo_climatico) if total else 0.0
            prediccion = self._prediccion_service.registrar(
                PrediccionRiesgo(
                    id_envio=envio.id_envio,
                    probabilidad_demora=round(float(probabilidad), 4),
                    riesgo_climatico=round(riesgo_climatico, 4),
                    riesgo_operativo=round(riesgo_operativo, 4),
                    features_entrada={"origen": "scikit-learn", **features},
                )
            )
            resultado.append(prediccion)
        return resultado
