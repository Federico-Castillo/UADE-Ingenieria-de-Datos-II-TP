"""Menú principal de la aplicación. Las entidades aún no implementadas quedan
como placeholder para no tener que tocar esta estructura en sesiones futuras."""
from app.cli.alerta_menu import menu_alerta
from app.cli.cliente_menu import menu_cliente
from app.cli.contenedor_menu import menu_contenedor
from app.cli.cuenta_corriente_menu import menu_cuenta_corriente
from app.cli.cuenta_corriente_pagable_menu import menu_cuenta_corriente_pagable
from app.cli.envio_menu import menu_envio
from app.cli.evento_logistico_menu import menu_evento_logistico
from app.cli.factura_menu import menu_factura
from app.cli.factura_recibida_menu import menu_factura_recibida
from app.cli.grupo_trabajo_menu import menu_grupo_trabajo
from app.cli.incidente_menu import menu_incidente
from app.cli.mensaje_menu import menu_mensaje
from app.cli.operador_logistico_menu import menu_operador_logistico
from app.cli.pago_emitido_menu import menu_pago_emitido
from app.cli.pago_menu import menu_pago
from app.cli.prediccion_riesgo_menu import menu_prediccion_riesgo
from app.cli.proveedor_menu import menu_proveedor
from app.cli.regla_menu import menu_regla
from app.cli.reporte_menu import menu_reporte
from app.cli.rol_menu import menu_rol
from app.cli.sensor_iot_menu import menu_sensor_iot
from app.cli.sesion_menu import menu_sesion
from app.cli.usuario_menu import menu_usuario
from app.cli.vehiculo_menu import menu_vehiculo

_PROXIMAMENTE = [
    "Monitoreo IoT (lecturas en Cassandra)",
    "Trazabilidad de recorrido (ruta en Neo4j)",
    "Inteligencia Analítica (rankings, scikit-learn)",
]


def _mostrar_proximamente(nombre: str) -> None:
    print(f"\n'{nombre}' todavía no está implementado.")
    input("\nPresioná Enter para continuar...")


def menu_principal() -> None:
    opciones = [
        ("Gestión de Clientes", menu_cliente),
        ("Gestión de Usuarios", menu_usuario),
        ("Gestión de Roles", menu_rol),
        ("Gestión de Sesiones", menu_sesion),
        ("Gestión de Proveedores", menu_proveedor),
        ("Gestión de Operadores Logísticos", menu_operador_logistico),
        ("Gestión de Contenedores", menu_contenedor),
        ("Gestión de Sensores IoT", menu_sensor_iot),
        ("Gestión de Vehículos", menu_vehiculo),
        ("Gestión de Envíos", menu_envio),
        ("Gestión de Reglas", menu_regla),
        ("Gestión de Alertas", menu_alerta),
        ("Gestión de Facturas (clientes)", menu_factura),
        ("Gestión de Pagos (clientes)", menu_pago),
        ("Cuentas Corrientes (clientes)", menu_cuenta_corriente),
        ("Gestión de Facturas Recibidas (proveedores/operadores)", menu_factura_recibida),
        ("Gestión de Pagos Emitidos (proveedores/operadores)", menu_pago_emitido),
        ("Cuentas Corrientes Pagables (proveedores/operadores)", menu_cuenta_corriente_pagable),
        ("Gestión de Reportes", menu_reporte),
        ("Eventos Logísticos (Mongo)", menu_evento_logistico),
        ("Incidentes (Mongo)", menu_incidente),
        ("Mensajería (Mongo)", menu_mensaje),
        ("Grupos de Trabajo (Mongo)", menu_grupo_trabajo),
        ("Predicciones de Riesgo (Mongo)", menu_prediccion_riesgo),
    ]
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
