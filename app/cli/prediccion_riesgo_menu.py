"""Menú de PrediccionRiesgo (MongoDB). El alta manual simula el resultado de
un proceso de predicción (scikit-learn, pendiente de implementar)."""
from app.cli.io_utils import leer_decimal, leer_entero, pausar
from app.core.exceptions import AppError
from app.domain.prediccion_riesgo import PrediccionRiesgo
from app.services.prediccion_riesgo_service import PrediccionRiesgoService


def _imprimir(p: PrediccionRiesgo) -> None:
    print(
        f"  [{p.id_prediccion}] envío {p.id_envio} | prob. demora {p.probabilidad_demora:.2f} | "
        f"riesgo climático {p.riesgo_climatico:.2f} | riesgo operativo {p.riesgo_operativo:.2f} | {p.fecha_calculo}"
    )


def _registrar(service: PrediccionRiesgoService) -> None:
    print("\n-- Registrar Predicción de Riesgo --")
    prediccion = PrediccionRiesgo(
        id_envio=leer_entero("ID de envío"),
        probabilidad_demora=leer_decimal("Probabilidad de demora (0.0 a 1.0)"),
        riesgo_climatico=leer_decimal("Riesgo climático (0.0 a 1.0)"),
        riesgo_operativo=leer_decimal("Riesgo operativo (0.0 a 1.0)"),
    )
    creada = service.registrar(prediccion)
    print(f"Predicción registrada con id {creada.id_prediccion}.")


def _ultima_por_envio(service: PrediccionRiesgoService) -> None:
    print("\n-- Última Predicción de un Envío --")
    id_envio = leer_entero("ID de envío")
    prediccion = service.ultima_por_envio(id_envio)
    if prediccion is None:
        print("  Ese envío no tiene predicciones todavía.")
    else:
        _imprimir(prediccion)


def _listado_por_envio(service: PrediccionRiesgoService) -> None:
    print("\n-- Historial de Predicciones de un Envío --")
    id_envio = leer_entero("ID de envío")
    predicciones = service.listar_por_envio(id_envio)
    if not predicciones:
        print("  Ese envío no tiene predicciones.")
    for p in predicciones:
        _imprimir(p)


_ACCIONES = {
    "1": ("Registrar predicción", _registrar),
    "2": ("Última predicción de un envío", _ultima_por_envio),
    "3": ("Historial de un envío", _listado_por_envio),
}


def menu_prediccion_riesgo() -> None:
    service = PrediccionRiesgoService()
    while True:
        print("\n=== Predicciones de Riesgo (MongoDB) ===")
        for key, (nombre, _) in _ACCIONES.items():
            print(f"{key}) {nombre}")
        print("0) Volver")
        opcion = input("Elegí una opción: ").strip()
        if opcion == "0":
            return
        accion = _ACCIONES.get(opcion)
        if accion is None:
            print("Opción inválida.")
            continue
        try:
            accion[1](service)
        except AppError as e:
            print(f"Error: {e}")
        pausar()
