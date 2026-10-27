"""Carga un set chico de datos de prueba en los 5 motores, para poder mostrar
cada ABM y que los procesos periódicos / reportes operativos no aparezcan
vacíos en la defensa. Reusa los Services existentes de punta a punta (no hay
SQL/Cypher/inserts nuevos acá, salvo la limpieza) para que los datos queden
tan válidos y consistentes como si se hubieran cargado a mano desde la CLI.

Todo el texto identificable (razón social, nombres, códigos) lleva el
prefijo 'DEMO_', igual que los tests usan 'TEST_' — esto permite volver a
correr el script sin acumular duplicados (limpia antes de cargar) y nunca
pisa datos reales que el usuario haya cargado a mano.

Al final corre, además, los procesos periódicos (cierre mensual y detección
de sensores inactivos) para que no aparezcan vacíos. Ojo: la detección de
sensores inactivos evalúa TODOS los sensores con estado='activo' de la base
(no solo los DEMO_), así que si había sensores reales sin lecturas recientes
de antes, también van a quedar marcados 'inactivo' como efecto colateral
real del proceso (no es un bug: es justamente lo que hace la función).

Uso:
    python scripts/seed_datos_prueba.py              # limpia y carga
    python scripts/seed_datos_prueba.py --solo-limpiar
"""
import argparse
import os
import random
import sys
from datetime import timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.exceptions import AppError
from app.db.mongo import get_db
from app.db.mysql import transaction
from app.db.neo4j_driver import session as neo4j_session
from app.domain.cliente import Cliente
from app.domain.contenedor import Contenedor
from app.domain.envio import Envio
from app.domain.evento_logistico import EventoLogistico
from app.domain.factura import Factura
from app.domain.factura_recibida import FacturaRecibida
from app.domain.grupo_trabajo import GrupoTrabajo
from app.domain.incidente import Incidente
from app.domain.mensaje import Mensaje
from app.domain.operador_logistico import OperadorLogistico
from app.domain.pago import Pago
from app.domain.pago_emitido import PagoEmitido
from app.domain.prediccion_riesgo import PrediccionRiesgo
from app.domain.proveedor import Proveedor
from app.domain.regla import Regla
from app.domain.reporte import Reporte
from app.domain.rol import Rol
from app.domain.sensor_iot import SensorIoT
from app.domain.tramo import Tramo
from app.domain.usuario import Usuario
from app.domain.vehiculo import Vehiculo
from app.logging_config import setup_logging
from app.services.cierre_cuenta_corriente_service import CierreCuentaCorrienteService
from app.services.cliente_service import ClienteService
from app.services.contenedor_service import ContenedorService
from app.services.envio_contenedor_service import EnvioContenedorService
from app.services.envio_service import EnvioService
from app.services.evento_logistico_service import EventoLogisticoService
from app.services.factura_recibida_service import FacturaRecibidaService
from app.services.factura_service import FacturaService
from app.services.grupo_trabajo_service import GrupoTrabajoService
from app.services.incidente_service import IncidenteService
from app.services.lectura_sensor_service import LecturaSensorService
from app.services.mensaje_service import MensajeService
from app.services.operador_logistico_service import OperadorLogisticoService
from app.services.pago_emitido_service import PagoEmitidoService
from app.services.pago_service import PagoService
from app.services.prediccion_riesgo_service import PrediccionRiesgoService
from app.services.proveedor_service import ProveedorService
from app.services.regla_service import ReglaService
from app.services.reporte_service import ReporteService
from app.services.rol_service import RolService
from app.services.sensor_inactivo_service import SensorInactivoService
from app.services.sensor_iot_service import SensorIoTService
from app.services.tramo_service import TramoService
from app.services.usuario_service import UsuarioService
from app.services.vehiculo_service import VehiculoService
from scripts.simulador_iot import ejecutar_tick

PREFIX = "DEMO_"
_PASSWORD = "Demo12345"


def limpiar_datos_demo() -> None:
    """Mismo criterio (y mismo orden por FK) que la limpieza autouse de
    tests/conftest.py, pero con el prefijo DEMO_ en vez de TEST_."""
    like = f"{PREFIX}%"
    with transaction() as cursor:
        cursor.execute("DELETE FROM reporte WHERE tipo LIKE %s", (like,))
        cursor.execute("DELETE FROM regla WHERE nombre LIKE %s", (like,))
        cursor.execute(
            "DELETE FROM envio_contenedor WHERE "
            "id_envio IN (SELECT id_envio FROM envio WHERE origen LIKE %s) OR "
            "id_contenedor IN (SELECT id_contenedor FROM contenedor WHERE codigo_internacional LIKE %s)",
            (like, like),
        )
        cursor.execute("DELETE FROM envio WHERE origen LIKE %s", (like,))
        cursor.execute(
            "DELETE FROM sensor_iot WHERE id_contenedor IN "
            "(SELECT id_contenedor FROM contenedor WHERE codigo_internacional LIKE %s)",
            (like,),
        )
        cursor.execute("DELETE FROM usuario WHERE nombre LIKE %s", (like,))
        cursor.execute(
            "DELETE FROM pago WHERE id_factura IN "
            "(SELECT id_factura FROM factura WHERE id_cliente IN "
            "(SELECT id_cliente FROM cliente WHERE razon_social LIKE %s))",
            (like,),
        )
        cursor.execute(
            "DELETE FROM factura WHERE id_cliente IN "
            "(SELECT id_cliente FROM cliente WHERE razon_social LIKE %s)",
            (like,),
        )
        cursor.execute(
            "DELETE FROM cierre_cuenta_corriente WHERE id_cliente IN "
            "(SELECT id_cliente FROM cliente WHERE razon_social LIKE %s)",
            (like,),
        )
        cursor.execute(
            "DELETE FROM cuenta_corriente WHERE id_cliente IN "
            "(SELECT id_cliente FROM cliente WHERE razon_social LIKE %s)",
            (like,),
        )
        cursor.execute("DELETE FROM cliente WHERE razon_social LIKE %s", (like,))
        cursor.execute("DELETE FROM rol WHERE descripcion LIKE %s", (like,))
        cursor.execute(
            "DELETE FROM pago_emitido WHERE id_factura_recibida IN "
            "(SELECT id_factura_recibida FROM factura_recibida WHERE "
            "id_proveedor IN (SELECT id_proveedor FROM proveedor WHERE razon_social LIKE %s) OR "
            "id_operador_logistico IN (SELECT id_operador_logistico FROM operador_logistico WHERE razon_social LIKE %s))",
            (like, like),
        )
        cursor.execute(
            "DELETE FROM factura_recibida WHERE "
            "id_proveedor IN (SELECT id_proveedor FROM proveedor WHERE razon_social LIKE %s) OR "
            "id_operador_logistico IN (SELECT id_operador_logistico FROM operador_logistico WHERE razon_social LIKE %s)",
            (like, like),
        )
        cursor.execute(
            "DELETE FROM cierre_cuenta_corriente_pagable WHERE "
            "id_proveedor IN (SELECT id_proveedor FROM proveedor WHERE razon_social LIKE %s) OR "
            "id_operador_logistico IN (SELECT id_operador_logistico FROM operador_logistico WHERE razon_social LIKE %s)",
            (like, like),
        )
        cursor.execute(
            "DELETE FROM cuenta_corriente_pagable WHERE "
            "id_proveedor IN (SELECT id_proveedor FROM proveedor WHERE razon_social LIKE %s) OR "
            "id_operador_logistico IN (SELECT id_operador_logistico FROM operador_logistico WHERE razon_social LIKE %s)",
            (like, like),
        )
        cursor.execute("DELETE FROM proveedor WHERE razon_social LIKE %s", (like,))
        cursor.execute("DELETE FROM operador_logistico WHERE razon_social LIKE %s", (like,))
        cursor.execute("DELETE FROM contenedor WHERE codigo_internacional LIKE %s", (like,))
        cursor.execute("DELETE FROM vehiculo WHERE identificacion LIKE %s", (like,))

    db = get_db()
    # Los eventos de entrega necesitan tipo_evento='entregado' fijo (no puede
    # llevar el prefijo), por eso se marcan vía 'descripcion' en vez de tipo.
    db["eventos_logisticos"].delete_many({"descripcion": {"$regex": f"^{PREFIX}"}})
    db["incidentes"].delete_many({"tipo": {"$regex": f"^{PREFIX}"}})
    db["mensajes"].delete_many({"contenido": {"$regex": f"^{PREFIX}"}})
    db["grupos_trabajo"].delete_many({"nombre": {"$regex": f"^{PREFIX}"}})
    # predicciones_riesgo no tiene campos de texto propios: se marcan con un
    # flag dentro de features_entrada (dict libre) para poder filtrarlas.
    db["predicciones_riesgo"].delete_many({"features_entrada.demo": True})

    with neo4j_session() as sess:
        sess.run(
            """
            MATCH (c:Cliente) WHERE c.razon_social STARTS WITH $prefix
            OPTIONAL MATCH (c)-[:SOLICITA]->(e:Envio)
            OPTIONAL MATCH (e)-[:INCLUYE]->(t:Tramo)
            OPTIONAL MATCH (t)-[:ORIGEN]->(o:Ubicacion)
            OPTIONAL MATCH (t)-[:DESTINO]->(d:Ubicacion)
            DETACH DELETE c, e, t, o, d
            """,
            prefix=PREFIX,
        )
        sess.run("MATCH (v:Vehiculo) WHERE v.identificacion STARTS WITH $prefix DETACH DELETE v", prefix=PREFIX)
        sess.run("MATCH (o:Operador) WHERE o.nombre STARTS WITH $prefix DETACH DELETE o", prefix=PREFIX)
        sess.run("MATCH (u:Ubicacion) WHERE u.nombre STARTS WITH $prefix DETACH DELETE u", prefix=PREFIX)

    print("Datos de prueba anteriores eliminados (si había).")


def _crear_roles_y_usuarios() -> tuple[list, list]:
    rol_admin = RolService().dar_alta(Rol(descripcion=f"{PREFIX}Administrador", nivel_permisos=10))
    rol_operador = RolService().dar_alta(Rol(descripcion=f"{PREFIX}Operador", nivel_permisos=5))
    usuarios = [
        UsuarioService().dar_alta(
            Usuario(nombre=f"{PREFIX}Ana", apellido="Gomez", email="demo.ana@example.com", id_rol=rol_admin.id_rol),
            _PASSWORD,
        ),
        UsuarioService().dar_alta(
            Usuario(nombre=f"{PREFIX}Luis", apellido="Perez", email="demo.luis@example.com", id_rol=rol_operador.id_rol),
            _PASSWORD,
        ),
    ]
    return [rol_admin, rol_operador], usuarios


def _crear_clientes() -> list:
    datos = [
        ("Agropecuaria del Sur", "Argentina"),
        ("Importadora Andina", "Chile"),
        ("Textiles do Brasil", "Brasil"),
        ("Comercial Ibérica", "España"),
        ("Distribuidora Azteca", "México"),
        ("Frigorífico Uruguayo", "Uruguay"),
    ]
    clientes = []
    for i, (nombre, pais) in enumerate(datos, start=1):
        clientes.append(
            ClienteService().dar_alta(
                Cliente(
                    razon_social=f"{PREFIX}{nombre}",
                    cuit=f"30-{70000000 + i:08d}-1",
                    email=f"demo.cliente{i}@example.com",
                    pais=pais,
                )
            )
        )
    return clientes


def _crear_proveedores_y_operadores() -> tuple[list, list]:
    proveedores = [
        ProveedorService().dar_alta(
            Proveedor(
                razon_social=f"{PREFIX}Proveedor {n}",
                cuit=f"30-{71000000 + i:08d}-1",
                email=f"demo.proveedor{i}@example.com",
            )
        )
        for i, n in enumerate(["Repuestos SA", "Combustibles SRL", "Embalajes SA"], start=1)
    ]
    operadores = [
        OperadorLogisticoService().dar_alta(
            OperadorLogistico(
                razon_social=f"{PREFIX}Operador {n}",
                cuit=f"30-{72000000 + i:08d}-1",
                email=f"demo.operador{i}@example.com",
            )
        )
        for i, n in enumerate(["Transportes del Plata", "Naviera Austral", "Aerocargo"], start=1)
    ]
    return proveedores, operadores


def _crear_vehiculos() -> list:
    datos = [
        ("camion", "Transportes del Plata"),
        ("camion", "Transportes del Plata"),
        ("barco", "Naviera Austral"),
        ("avion", "Aerocargo"),
    ]
    return [
        VehiculoService().dar_alta(
            Vehiculo(tipo=tipo, identificacion=f"{PREFIX}VEH{i:02d}", empresa_operadora=f"{PREFIX}{empresa}")
        )
        for i, (tipo, empresa) in enumerate(datos, start=1)
    ]


def _crear_contenedores_y_sensores() -> tuple[list, list]:
    contenedores = [
        ContenedorService().dar_alta(
            Contenedor(codigo_internacional=f"{PREFIX}CONT{i:02d}", tipo="reefer" if i % 2 == 0 else "dry", capacidad=20.0)
        )
        for i in range(1, 9)
    ]
    tipos_sensor = ["temperatura", "humedad", "vibracion", "bateria"]
    sensores = [
        SensorIoTService().dar_alta(
            SensorIoT(id_contenedor=contenedor.id_contenedor, tipo=tipos_sensor[i % len(tipos_sensor)])
        )
        for i, contenedor in enumerate(contenedores)
    ]
    return contenedores, sensores


def _crear_reglas(usuarios: list) -> list:
    datos = [
        ("temperatura", ">", 35.0, "critica"),
        ("humedad", ">", 90.0, "alta"),
        ("vibracion", ">", 4.0, "media"),
        ("bateria", "<", 15.0, "alta"),
    ]
    return [
        ReglaService().dar_alta(
            Regla(
                nombre=f"{PREFIX}Regla_{tipo}",
                tipo_sensor=tipo,
                operador_comparacion=op,
                valor_umbral=umbral,
                severidad=severidad,
                id_usuario_creador=usuarios[0].id_usuario,
            )
        )
        for tipo, op, umbral, severidad in datos
    ]


def _crear_envios(clientes: list) -> list:
    estados = ["pendiente", "en_transito", "entregado", "entregado", "demorado", "cancelado"]
    destinos = ["Madrid", "São Paulo", "Santiago", "Ciudad de México", "Montevideo", "Rotterdam"]
    servicio = EnvioService()
    envios = []
    for i in range(18):
        cliente = clientes[i % len(clientes)]
        creado = servicio.dar_alta(
            Envio(
                id_cliente=cliente.id_cliente,
                origen=f"{PREFIX}Origen{i + 1}",
                destino=destinos[i % len(destinos)],
                estado=estados[i % len(estados)],
                prioridad=random.choice(["baja", "normal", "alta", "urgente"]),
            )
        )
        # dar_alta no devuelve fecha_creacion (la pone MySQL con DEFAULT
        # CURRENT_TIMESTAMP); se necesita el valor real para los cálculos de
        # tiempos de entrega más abajo.
        envios.append(servicio.obtener_por_id(creado.id_envio))
    return envios


def _asignar_contenedores(envios: list, contenedores: list) -> None:
    servicio = EnvioContenedorService()
    for i, contenedor in enumerate(contenedores):
        envio = envios[i % len(envios)]
        servicio.asignar_contenedor(envio.id_envio, contenedor.id_contenedor)


def _crear_facturacion_clientes(clientes: list) -> None:
    factura_service = FacturaService()
    pago_service = PagoService()
    for i, cliente in enumerate(clientes):
        factura = factura_service.dar_alta(Factura(id_cliente=cliente.id_cliente, importe_total=1000.0 * (i + 1)))
        if i % 3 == 0:
            pago_service.registrar_pago(Pago(id_factura=factura.id_factura, monto=factura.importe_total, medio_pago="transferencia"))
        elif i % 3 == 1:
            pago_service.registrar_pago(
                Pago(id_factura=factura.id_factura, monto=factura.importe_total / 2, medio_pago="transferencia")
            )
        # el resto queda pendiente, para que haya variedad de saldos


def _crear_facturacion_pagable(proveedores: list, operadores: list) -> None:
    factura_service = FacturaRecibidaService()
    pago_service = PagoEmitidoService()
    for i, proveedor in enumerate(proveedores):
        factura = factura_service.dar_alta(FacturaRecibida(importe_total=500.0 * (i + 1), id_proveedor=proveedor.id_proveedor))
        if i % 2 == 0:
            pago_service.registrar_pago(
                PagoEmitido(id_factura_recibida=factura.id_factura_recibida, monto=factura.importe_total, medio_pago="transferencia")
            )
    for i, operador in enumerate(operadores):
        factura_service.dar_alta(FacturaRecibida(importe_total=800.0 * (i + 1), id_operador_logistico=operador.id_operador_logistico))


def _crear_tramos_y_eventos(envios: list, vehiculos: list, operadores: list) -> None:
    tramo_service = TramoService()
    evento_service = EventoLogisticoService()
    medios = ["terrestre", "maritimo", "aereo"]
    envios_con_tramo = envios[:10]
    for i, envio in enumerate(envios_con_tramo):
        medio = medios[i % len(medios)]
        costo = round(random.uniform(500, 5000), 2) if i % 4 != 3 else None  # alguno sin costo a propósito
        tramo_service.registrar_tramo(
            Tramo(
                id_envio=envio.id_envio,
                medio_transporte=medio,
                id_vehiculo=vehiculos[i % len(vehiculos)].id_vehiculo,
                id_operador_logistico=operadores[i % len(operadores)].id_operador_logistico,
                origen_nombre=f"{PREFIX}Origen{i + 1}",
                destino_nombre=envio.destino,
                origen_pais="Argentina",
                destino_pais="Exterior",
                fecha_salida=envio.fecha_creacion,
                fecha_llegada_estimada=(envio.fecha_creacion + timedelta(days=5)) if envio.fecha_creacion else None,
                costo=costo,
            )
        )
        evento_service.registrar(
            EventoLogistico(id_envio=envio.id_envio, tipo_evento="carga_iniciada", descripcion=f"{PREFIX}evento_carga")
        )
        if envio.estado == "entregado" and envio.fecha_creacion is not None:
            evento_service.registrar(
                EventoLogistico(
                    id_envio=envio.id_envio,
                    tipo_evento="entregado",
                    descripcion=f"{PREFIX}evento_entrega",
                    fecha_hora=envio.fecha_creacion + timedelta(hours=random.uniform(12, 96)),
                )
            )


def _crear_incidentes(envios: list) -> None:
    servicio = IncidenteService()
    datos = [
        (envios[2], "demora_aduana", "media"),
        (envios[4], "rotura_embalaje", "alta"),
    ]
    for envio, tipo, severidad in datos:
        servicio.registrar(
            Incidente(
                id_envio=envio.id_envio,
                tipo=f"{PREFIX}{tipo}",
                severidad=severidad,
                descripcion=f"{PREFIX}Incidente de prueba para la defensa.",
            )
        )


def _crear_mensajeria(usuarios: list) -> None:
    grupo = GrupoTrabajoService().crear(
        GrupoTrabajo(nombre=f"{PREFIX}Equipo Logística", integrantes=[u.id_usuario for u in usuarios])
    )
    mensaje_service = MensajeService()
    mensaje_service.enviar(
        Mensaje(
            id_remitente=usuarios[0].id_usuario,
            id_destinatario=usuarios[1].id_usuario,
            contenido=f"{PREFIX}¿Revisaste el envío demorado?",
            tipo="privado",
        )
    )
    mensaje_service.enviar(
        Mensaje(
            id_remitente=usuarios[1].id_usuario,
            id_grupo=grupo.id_grupo,
            contenido=f"{PREFIX}Arranca la ronda de seguimiento semanal.",
            tipo="grupal",
        )
    )


def _crear_predicciones(envios: list) -> None:
    servicio = PrediccionRiesgoService()
    probabilidades = [0.15, 0.3, 0.45, 0.65, 0.85]
    for i, envio in enumerate(envios[:5]):
        servicio.registrar(
            PrediccionRiesgo(
                id_envio=envio.id_envio,
                probabilidad_demora=probabilidades[i],
                riesgo_climatico=round(random.uniform(0.1, 0.9), 2),
                riesgo_operativo=round(random.uniform(0.1, 0.9), 2),
                features_entrada={"demo": True},
            )
        )


def _crear_reportes_metadata(usuarios: list) -> None:
    servicio = ReporteService()
    for tipo in [f"{PREFIX}envios_por_pais", f"{PREFIX}incidentes_promedio_por_cliente"]:
        servicio.generar(Reporte(id_usuario=usuarios[0].id_usuario, tipo=tipo, formato="pdf"))


def _generar_actividad_derivada(sensores: list) -> None:
    """Deja 2 sensores sin ninguna lectura a propósito, para que la
    detección de sensores inactivos tenga algo real para mostrar."""
    lectura_service = LecturaSensorService()
    sensores_con_lectura = sensores[:-2]
    for _ in range(3):
        ejecutar_tick(lectura_service, sensores_con_lectura, prob_anomalia=0.4)

    resultado_cierre = CierreCuentaCorrienteService().ejecutar_cierre_mensual()
    print(f"Cierre mensual ejecutado: {resultado_cierre}")

    inactivos = SensorInactivoService().marcar_inactivos()
    print(f"Sensores marcados inactivos: {[s.id_sensor for s in inactivos]}")


def seed() -> None:
    limpiar_datos_demo()

    _, usuarios = _crear_roles_y_usuarios()
    clientes = _crear_clientes()
    proveedores, operadores = _crear_proveedores_y_operadores()
    vehiculos = _crear_vehiculos()
    contenedores, sensores = _crear_contenedores_y_sensores()
    _crear_reglas(usuarios)
    envios = _crear_envios(clientes)
    _asignar_contenedores(envios, contenedores)
    _crear_facturacion_clientes(clientes)
    _crear_facturacion_pagable(proveedores, operadores)
    _crear_tramos_y_eventos(envios, vehiculos, operadores)
    _crear_incidentes(envios)
    _crear_mensajeria(usuarios)
    _crear_predicciones(envios)
    _crear_reportes_metadata(usuarios)

    print(
        f"Datos base cargados: {len(clientes)} clientes, {len(proveedores)} proveedores, "
        f"{len(operadores)} operadores, {len(vehiculos)} vehículos, {len(contenedores)} contenedores, "
        f"{len(sensores)} sensores, {len(envios)} envíos."
    )

    _generar_actividad_derivada(sensores)
    print("Listo. Recorré los menús de la app para ver los datos cargados.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--solo-limpiar", action="store_true", help="Solo borra los datos DEMO_, no carga nada nuevo")
    args = parser.parse_args()

    setup_logging()
    try:
        if args.solo_limpiar:
            limpiar_datos_demo()
        else:
            seed()
    except AppError as e:
        print(f"Error: {e}")
        raise


if __name__ == "__main__":
    main()
