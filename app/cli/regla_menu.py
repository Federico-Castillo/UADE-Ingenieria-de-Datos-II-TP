"""Menú ABM de Regla (parte de "ABM Reglas y Alertas" junto con Alerta en Redis)."""
from app.cli.io_utils import confirmar, leer_decimal, leer_entero, leer_no_vacio, leer_opcion, limpiar_pantalla, pausar
from app.core.exceptions import AppError
from app.domain.regla import Regla
from app.services.regla_service import ReglaService

_OPERADORES = {">", ">=", "<", "<=", "="}
_SEVERIDADES = {"baja", "media", "alta", "critica"}


def _imprimir(r: Regla) -> None:
    print(
        f"  [{r.id_regla}] {r.nombre} | {r.tipo_sensor} {r.operador_comparacion} {r.valor_umbral} | "
        f"severidad {r.severidad} | {r.estado}"
    )


def _alta(service: ReglaService) -> None:
    print("\n-- Alta de Regla --")
    regla = Regla(
        nombre=leer_no_vacio("Nombre"),
        tipo_sensor=leer_no_vacio("Tipo de sensor (temperatura/humedad/vibracion/bateria)"),
        operador_comparacion=leer_opcion(f"Operador ({'/'.join(sorted(_OPERADORES))})", _OPERADORES),
        valor_umbral=leer_decimal("Valor umbral"),
        severidad=leer_opcion(f"Severidad ({'/'.join(sorted(_SEVERIDADES))})", _SEVERIDADES),
        id_usuario_creador=leer_entero("ID de usuario creador"),
    )
    creada = service.dar_alta(regla)
    print(f"Regla creada con id {creada.id_regla}.")


def _baja(service: ReglaService) -> None:
    print("\n-- Baja de Regla --")
    id_regla = leer_entero("ID de regla a eliminar")
    regla = service.obtener_por_id(id_regla)
    _imprimir(regla)
    if confirmar("¿Confirmás eliminar esta regla?"):
        service.eliminar(id_regla)
        print("Regla eliminada.")
    else:
        print("Operación cancelada.")


def _modificacion(service: ReglaService) -> None:
    print("\n-- Modificación de Regla --")
    id_regla = leer_entero("ID de regla a modificar")
    regla = service.obtener_por_id(id_regla)
    _imprimir(regla)
    print("Dejá vacío para mantener el valor actual.")
    regla.nombre = input(f"Nombre [{regla.nombre}]: ").strip() or regla.nombre
    umbral_str = input(f"Valor umbral [{regla.valor_umbral}]: ").strip().replace(",", ".")
    try:
        regla.valor_umbral = float(umbral_str)
    except ValueError:
        pass
    if confirmar("¿Querés cambiar el estado?"):
        regla.estado = leer_opcion(f"Estado [{regla.estado}] (activa/inactiva)", {"activa", "inactiva"})
    service.modificar(regla)
    print("Regla modificada.")


def _listado(service: ReglaService) -> None:
    print("\n-- Listado de Reglas --")
    solo_activas = confirmar("¿Listar solo activas?")
    reglas = service.listar(solo_activas=solo_activas)
    if not reglas:
        print("  No hay reglas para mostrar.")
    for r in reglas:
        _imprimir(r)


_ACCIONES = {
    "1": ("Alta", _alta),
    "2": ("Baja", _baja),
    "3": ("Modificación", _modificacion),
    "4": ("Listado", _listado),
}


def menu_regla() -> None:
    service = ReglaService()
    while True:
        limpiar_pantalla()
        print("\n=== Gestión de Reglas ===")
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
