"""Menú ABM de Contenedor."""
from app.cli.io_utils import confirmar, leer_decimal, leer_entero, leer_no_vacio, limpiar_pantalla, pausar
from app.core.exceptions import AppError
from app.domain.contenedor import Contenedor
from app.services.contenedor_service import ContenedorService


def _imprimir(c: Contenedor) -> None:
    print(f"  [{c.id_contenedor}] {c.codigo_internacional} | {c.tipo} | cap. {c.capacidad} | {c.estado}")


def _alta(service: ContenedorService) -> None:
    print("\n-- Alta de Contenedor --")
    contenedor = Contenedor(
        codigo_internacional=leer_no_vacio("Código internacional"),
        tipo=leer_no_vacio("Tipo"),
        capacidad=leer_decimal("Capacidad"),
    )
    creado = service.dar_alta(contenedor)
    print(f"Contenedor creado con id {creado.id_contenedor}.")


def _baja(service: ContenedorService) -> None:
    print("\n-- Baja de Contenedor --")
    id_contenedor = leer_entero("ID de contenedor a eliminar")
    contenedor = service.obtener_por_id(id_contenedor)
    _imprimir(contenedor)
    if confirmar("¿Confirmás eliminar este contenedor?"):
        service.eliminar(id_contenedor)
        print("Contenedor eliminado.")
    else:
        print("Operación cancelada.")


def _modificacion(service: ContenedorService) -> None:
    print("\n-- Modificación de Contenedor --")
    id_contenedor = leer_entero("ID de contenedor a modificar")
    contenedor = service.obtener_por_id(id_contenedor)
    _imprimir(contenedor)
    print("Dejá vacío para mantener el valor actual.")
    contenedor.codigo_internacional = (
        input(f"Código internacional [{contenedor.codigo_internacional}]: ").strip()
        or contenedor.codigo_internacional
    )
    contenedor.tipo = input(f"Tipo [{contenedor.tipo}]: ").strip() or contenedor.tipo
    capacidad_str = input(f"Capacidad [{contenedor.capacidad}]: ").strip().replace(",", ".")
    try:
        contenedor.capacidad = float(capacidad_str)
    except ValueError:
        pass
    contenedor.estado = input(f"Estado [{contenedor.estado}]: ").strip() or contenedor.estado
    service.modificar(contenedor)
    print("Contenedor modificado.")


def _listado(service: ContenedorService) -> None:
    print("\n-- Listado de Contenedores --")
    contenedores = service.listar()
    if not contenedores:
        print("  No hay contenedores para mostrar.")
    for c in contenedores:
        _imprimir(c)


def _busqueda(service: ContenedorService) -> None:
    print("\n-- Búsqueda de Contenedores --")
    texto = leer_no_vacio("Texto a buscar (código o tipo)")
    contenedores = service.buscar(texto)
    if not contenedores:
        print("  No se encontraron contenedores.")
    for c in contenedores:
        _imprimir(c)


_ACCIONES = {
    "1": ("Alta", _alta),
    "2": ("Baja", _baja),
    "3": ("Modificación", _modificacion),
    "4": ("Listado", _listado),
    "5": ("Búsqueda", _busqueda),
}


def menu_contenedor() -> None:
    service = ContenedorService()
    while True:
        limpiar_pantalla()
        print("\n=== Gestión de Contenedores ===")
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
