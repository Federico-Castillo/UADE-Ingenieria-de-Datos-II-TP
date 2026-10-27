"""Menú principal de la aplicación. Las entidades aún no implementadas quedan
como placeholder para no tener que tocar esta estructura en sesiones futuras."""
from app.cli.cliente_menu import menu_cliente

_PROXIMAMENTE = [
    "Gestión de Usuarios y Roles",
    "Gestión de Sesiones activas",
    "Gestión de Proveedores",
    "Gestión de Operadores Logísticos",
    "Gestión de Envíos / Contenedores / Sensores",
    "Gestión de Reglas y Alertas",
    "Cuenta Corriente y Facturación",
    "Monitoreo IoT",
    "Trazabilidad de envíos",
    "Mensajería",
    "Reportes",
    "Inteligencia Analítica",
]


def _mostrar_proximamente(nombre: str) -> None:
    print(f"\n'{nombre}' todavía no está implementado.")
    input("\nPresioná Enter para continuar...")


def menu_principal() -> None:
    opciones = [("Gestión de Clientes", menu_cliente)]
    opciones += [(nombre, lambda n=nombre: _mostrar_proximamente(n)) for nombre in _PROXIMAMENTE]

    while True:
        print("\n===== TP Persistencia Políglota — Menú Principal =====")
        for i, (nombre, _) in enumerate(opciones, start=1):
            print(f"{i}) {nombre}")
        print("0) Salir")
        opcion = input("Elegí una opción: ").strip()
        if opcion == "0":
            print("¡Hasta luego!")
            return
        if not opcion.isdigit() or not (1 <= int(opcion) <= len(opciones)):
            print("Opción inválida.")
            continue
        _, accion = opciones[int(opcion) - 1]
        accion()
