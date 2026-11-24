"""Carga UN envío de ejemplo completo (Córdoba -> Dubái, con 3 tramos y todos
los datos relacionados en los 5 motores), para mostrar cómo se ve una
operación de punta a punta. Reusa los Services existentes, igual que
seed_datos_prueba.py, así que los datos son tan válidos como los cargados a
mano.

Todo lleva el prefijo 'DEMO_EJ_' (que además empieza con 'DEMO_'): volver a
correr el script reemplaza el ejemplo anterior sin tocar el resto de los
datos, y `seed_datos_prueba.py --solo-limpiar` también lo elimina.

Qué crea:
  MySQL      cliente, 3 operadores logísticos, proveedor, 3 vehículos,
             2 contenedores con 4 sensores cada uno, reglas, envío en tránsito
             con ambos contenedores asignados, factura al cliente con pagos
             parciales y facturas recibidas (operadores y proveedor) con pagos.
  Neo4j      los 3 tramos encadenados (ruta completa del envío).
  Cassandra  lecturas de los 8 sensores a lo largo de la ruta, con GPS.
  Redis      alerta generada por una lectura de temperatura fuera de rango.
  MongoDB    eventos logísticos, incidentes (uno manual y uno automático por la
             regla), predicción de riesgo, grupo de trabajo y mensajes.

Uso:
    python scripts/seed_envio_completo.py              # limpia el ejemplo y lo carga
    python scripts/seed_envio_completo.py --solo-limpiar
"""
import argparse
import os
import sys
from datetime import date, datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.exceptions import AppError
from app.db.mongo import get_db
from app.db.mysql import get_cursor
from app.domain.cliente import Cliente
from app.domain.contenedor import Contenedor
from app.domain.envio import Envio
from app.domain.evento_logistico import EventoLogistico
from app.domain.factura import Factura
from app.domain.factura_recibida import FacturaRecibida
from app.domain.grupo_trabajo import GrupoTrabajo
from app.domain.incidente import Incidente
from app.domain.lectura_sensor import LecturaSensor
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
from app.services.sensor_iot_service import SensorIoTService
from app.services.tramo_service import TramoService
from app.services.usuario_service import UsuarioService
from app.services.vehiculo_service import VehiculoService
from scripts.seed_datos_prueba import PREFIX as PREFIX_DEMO
from scripts.seed_datos_prueba import limpiar_datos_demo

PREFIX = f"{PREFIX_DEMO}EJ_"
_PASSWORD = "Demo12345"

# (nombre, lat, lon): puntos de la ruta Córdoba -> Dubái.
CORDOBA = ("Córdoba", -31.4201, -64.1888)
BUENOS_AIRES = ("Buenos Aires (Puerto)", -34.6037, -58.3816)
JEBEL_ALI = ("Jebel Ali (Puerto)", 25.0118, 55.0613)
DUBAI = ("Dubái (Depósito)", 25.2048, 55.2708)

# Recorrido GPS (día desde la salida, lat, lon). El barco está hoy cerca del
# Cabo de Buena Esperanza, rumbo a Jebel Ali.
RECORRIDO = [
    (0.0, -31.4201, -64.1888),   # sale de Córdoba
    (1.0, -33.0, -61.5),         # ruta a Buenos Aires
    (2.0, -34.6037, -58.3816),   # llega al puerto
    (4.0, -34.6037, -58.3816),   # espera de zarpe / aduana
    (6.0, -33.5, -45.0),         # navegando Atlántico Sur
    (8.0, -35.5, -20.0),
    (10.0, -35.8, 5.0),
    (12.0, -35.2, 18.5),         # cerca del Cabo de Buena Esperanza
]


def _limpiar_ejemplo_anterior() -> None:
    """limpiar_datos_demo cubre MySQL, Neo4j y los documentos de Mongo con
    prefijo, pero los incidentes automáticos (tipo 'anomalia_...') no llevan
    prefijo: se borran acá por id_envio, antes de que desaparezca el envío."""
    with get_cursor() as cursor:
        cursor.execute("SELECT id_envio FROM envio WHERE origen LIKE %s", (f"{PREFIX}%",))
        ids = [row["id_envio"] for row in cursor.fetchall()]
    if ids:
        db = get_db()
        for coleccion in ("incidentes", "eventos_logisticos", "predicciones_riesgo"):
            db[coleccion].delete_many({"id_envio": {"$in": ids}})
    limpiar_datos_demo(PREFIX)


def _crear_actores():
    rol = RolService().dar_alta(Rol(descripcion=f"{PREFIX}Coordinador de tráfico", nivel_permisos=7))
    usuarios = [
        UsuarioService().dar_alta(
            Usuario(nombre=f"{PREFIX}Marta", apellido="Sosa", email="demo.ej.marta@example.com", id_rol=rol.id_rol),
            _PASSWORD,
        ),
        UsuarioService().dar_alta(
            Usuario(nombre=f"{PREFIX}Diego", apellido="Ferreyra", email="demo.ej.diego@example.com", id_rol=rol.id_rol),
            _PASSWORD,
        ),
    ]
    cliente = ClienteService().dar_alta(
        Cliente(
            razon_social=f"{PREFIX}Exportadora Cordobesa SA",
            cuit="30-79000001-1",
            email="demo.ej.cliente@example.com",
            pais="Argentina",
        )
    )
    proveedor = ProveedorService().dar_alta(
        Proveedor(razon_social=f"{PREFIX}Embalajes del Centro SRL", cuit="30-79100001-1", email="demo.ej.proveedor@example.com")
    )
    operadores = [
        OperadorLogisticoService().dar_alta(
            OperadorLogistico(razon_social=f"{PREFIX}{nombre}", cuit=f"30-7920000{i}-1", email=f"demo.ej.operador{i}@example.com")
        )
        for i, nombre in enumerate(["Transportes Pampeanos SA", "Naviera del Atlántico SA", "Gulf Inland Logistics"], start=1)
    ]
    vehiculos = [
        VehiculoService().dar_alta(
            Vehiculo(tipo=tipo, identificacion=f"{PREFIX}{ident}", empresa_operadora=operadores[i].razon_social)
        )
        for i, (tipo, ident) in enumerate([("camion", "CAM-AR-01"), ("barco", "BUQUE-ATL-07"), ("camion", "CAM-AE-12")])
    ]
    return usuarios, cliente, proveedor, operadores, vehiculos


def _crear_contenedores_y_sensores():
    contenedores = [
        ContenedorService().dar_alta(Contenedor(codigo_internacional=f"{PREFIX}CONT01", tipo="reefer", capacidad=20.0)),
        ContenedorService().dar_alta(Contenedor(codigo_internacional=f"{PREFIX}CONT02", tipo="dry", capacidad=20.0)),
    ]
    sensores = {}  # id_contenedor -> {tipo: SensorIoT}
    for contenedor in contenedores:
        sensores[contenedor.id_contenedor] = {
            tipo: SensorIoTService().dar_alta(
                SensorIoT(
                    id_contenedor=contenedor.id_contenedor,
                    tipo=tipo,
                    fabricante="Sensirion",
                    fecha_instalacion=date.today() - timedelta(days=30),
                )
            )
            for tipo in ("temperatura", "humedad", "vibracion", "bateria")
        }
    return contenedores, sensores


def _crear_reglas(usuario) -> None:
    # Umbrales altos a propósito: las reglas son globales y no deben disparar con
    # lecturas normales de otros datos (ni de los tests, que usan ~20 °C).
    for tipo, op, umbral, severidad in [("temperatura", ">", 25.0, "alta"), ("humedad", ">", 85.0, "media")]:
        ReglaService().dar_alta(
            Regla(
                nombre=f"{PREFIX}Regla_{tipo}",
                tipo_sensor=tipo,
                operador_comparacion=op,
                valor_umbral=umbral,
                severidad=severidad,
                id_usuario_creador=usuario.id_usuario,
            )
        )


def _crear_envio(cliente, contenedores):
    servicio = EnvioService()
    creado = servicio.dar_alta(
        Envio(
            id_cliente=cliente.id_cliente,
            origen=f"{PREFIX}{CORDOBA[0]}",
            destino=f"{PREFIX}Dubái",
            estado="en_transito",
            prioridad="alta",
        )
    )
    envio = servicio.obtener_por_id(creado.id_envio)
    for contenedor in contenedores:
        EnvioContenedorService().asignar_contenedor(envio.id_envio, contenedor.id_contenedor)
    return envio


def _crear_tramos(envio, vehiculos, operadores, salida: datetime) -> None:
    servicio = TramoService()
    definiciones = [
        # (medio, origen, destino, vehículo, operador, salida (días), llegada (días), costo)
        ("terrestre", CORDOBA, BUENOS_AIRES, 0, 0, 0, 2, 1800.0),
        ("maritimo", BUENOS_AIRES, JEBEL_ALI, 1, 1, 4, 30, 9500.0),
        ("terrestre", JEBEL_ALI, DUBAI, 2, 2, 31, 32, 650.0),
    ]
    for medio, origen, destino, i_veh, i_op, d_salida, d_llegada, costo in definiciones:
        servicio.registrar_tramo(
            Tramo(
                id_envio=envio.id_envio,
                medio_transporte=medio,
                id_vehiculo=vehiculos[i_veh].id_vehiculo,
                id_operador_logistico=operadores[i_op].id_operador_logistico,
                origen_nombre=f"{PREFIX}{origen[0]}",
                origen_pais="Argentina" if origen in (CORDOBA, BUENOS_AIRES) else "Emiratos Árabes Unidos",
                origen_lat=origen[1],
                origen_lon=origen[2],
                destino_nombre=f"{PREFIX}{destino[0]}",
                destino_pais="Argentina" if destino == BUENOS_AIRES else "Emiratos Árabes Unidos",
                destino_lat=destino[1],
                destino_lon=destino[2],
                fecha_salida=salida + timedelta(days=d_salida),
                fecha_llegada_estimada=salida + timedelta(days=d_llegada),
                costo=costo,
            )
        )


def _cargar_lecturas(sensores: dict, salida: datetime) -> None:
    """Una lectura por sensor en cada punto del recorrido. El contenedor
    refrigerado (CONT01) tiene una anomalía de temperatura en el día 8, que
    dispara la regla: Incidente (Mongo) + Alerta (Redis)."""
    servicio = LecturaSensorService()
    salida_utc = salida.replace(tzinfo=timezone.utc)
    for n, (dia, lat, lon) in enumerate(RECORRIDO):
        momento = salida_utc + timedelta(days=dia)
        for indice, por_tipo in enumerate(sensores.values()):
            es_reefer = indice == 0
            temperatura = (4.0 if es_reefer else 22.0) + 0.2 * n
            if es_reefer and dia == 8.0:
                temperatura = 28.5  # falla de refrigeración (umbral de la regla: 25 °C)
            valores = {
                "temperatura": {"temperatura": round(temperatura, 1)},
                "humedad": {"humedad": round(62.0 + 1.5 * n, 1)},
                "vibracion": {"vibracion": round(0.6 + 0.1 * (n % 3), 2)},
                "bateria": {"nivel_bateria": round(98.0 - 4.0 * n, 1)},
            }
            for tipo, sensor in por_tipo.items():
                servicio.registrar_lectura(
                    LecturaSensor(id_sensor=sensor.id_sensor, gps_lat=lat, gps_lon=lon, fecha_hora=momento, **valores[tipo])
                )


def _crear_eventos_e_incidentes(envio, salida: datetime) -> None:
    eventos = EventoLogisticoService()
    cronologia = [
        (0.0, "carga_iniciada", "carga de los contenedores en planta", CORDOBA),
        (0.2, "salida_origen", "el camión sale de Córdoba rumbo al puerto", CORDOBA),
        (2.0, "arribo_puerto", "llegada a la terminal de Buenos Aires", BUENOS_AIRES),
        (3.0, "inspeccion_aduana", "inspección aduanera y documentación de exportación", BUENOS_AIRES),
        (4.0, "zarpe", "el buque zarpa hacia Jebel Ali", BUENOS_AIRES),
        (12.0, "en_navegacion", "pasando por el Cabo de Buena Esperanza", ("Cabo de Buena Esperanza", -35.2, 18.5)),
    ]
    for dia, tipo, descripcion, (nombre, lat, lon) in cronologia:
        eventos.registrar(
            EventoLogistico(
                id_envio=envio.id_envio,
                tipo_evento=tipo,
                descripcion=f"{PREFIX}{descripcion}",
                ubicacion={"nombre": nombre, "lat": lat, "lon": lon},
                fecha_hora=salida + timedelta(days=dia),
            )
        )
    incidentes = IncidenteService()
    manual = incidentes.registrar(
        Incidente(
            id_envio=envio.id_envio,
            tipo=f"{PREFIX}demora_aduana",
            severidad="media",
            descripcion=f"{PREFIX}La inspección en Buenos Aires demoró un día por documentación incompleta.",
        )
    )
    incidentes.cambiar_estado(manual.id_incidente, "cerrado")


def _crear_prediccion(envio) -> None:
    PrediccionRiesgoService().registrar(
        PrediccionRiesgo(
            id_envio=envio.id_envio,
            probabilidad_demora=0.42,
            riesgo_climatico=0.30,
            riesgo_operativo=0.55,
            features_entrada={"demo": True, "origen": "ejemplo_completo", "prioridad": "alta", "tramos": 3},
        )
    )


def _crear_facturacion(cliente, proveedor, operadores) -> None:
    factura = FacturaService().dar_alta(Factura(id_cliente=cliente.id_cliente, importe_total=24000.0))
    pagos = PagoService()
    pagos.registrar_pago(Pago(id_factura=factura.id_factura, monto=12000.0, medio_pago="transferencia"))
    pagos.registrar_pago(Pago(id_factura=factura.id_factura, monto=4000.0, medio_pago="efectivo"))  # queda 'parcial'

    recibidas = FacturaRecibidaService()
    pagos_emitidos = PagoEmitidoService()
    f_op1 = recibidas.dar_alta(FacturaRecibida(importe_total=1800.0, id_operador_logistico=operadores[0].id_operador_logistico))
    pagos_emitidos.registrar_pago(
        PagoEmitido(id_factura_recibida=f_op1.id_factura_recibida, monto=1800.0, medio_pago="transferencia")
    )
    f_op2 = recibidas.dar_alta(FacturaRecibida(importe_total=9500.0, id_operador_logistico=operadores[1].id_operador_logistico))
    pagos_emitidos.registrar_pago(
        PagoEmitido(id_factura_recibida=f_op2.id_factura_recibida, monto=5000.0, medio_pago="transferencia")
    )
    recibidas.dar_alta(FacturaRecibida(importe_total=650.0, id_operador_logistico=operadores[2].id_operador_logistico))
    f_prov = recibidas.dar_alta(FacturaRecibida(importe_total=1200.0, id_proveedor=proveedor.id_proveedor))
    pagos_emitidos.registrar_pago(
        PagoEmitido(id_factura_recibida=f_prov.id_factura_recibida, monto=1200.0, medio_pago="efectivo")
    )


def _crear_mensajeria_y_reporte(usuarios) -> None:
    grupo = GrupoTrabajoService().crear(
        GrupoTrabajo(nombre=f"{PREFIX}Seguimiento Córdoba-Dubái", integrantes=[u.id_usuario for u in usuarios])
    )
    mensajes = MensajeService()
    mensajes.enviar(
        Mensaje(
            id_remitente=usuarios[0].id_usuario,
            id_grupo=grupo.id_grupo,
            contenido=f"{PREFIX}El buque pasó el Cabo de Buena Esperanza, ETA a Jebel Ali en 18 días.",
            tipo="grupal",
        )
    )
    mensajes.enviar(
        Mensaje(
            id_remitente=usuarios[1].id_usuario,
            id_destinatario=usuarios[0].id_usuario,
            contenido=f"{PREFIX}Salta una alerta de temperatura en CONT01, ¿lo revisamos con la naviera?",
            tipo="privado",
        )
    )
    ReporteService().generar(Reporte(id_usuario=usuarios[0].id_usuario, tipo=f"{PREFIX}envios_por_pais", formato="pdf"))


def cargar_ejemplo() -> None:
    _limpiar_ejemplo_anterior()
    salida = datetime.now().replace(microsecond=0) - timedelta(days=12)

    usuarios, cliente, proveedor, operadores, vehiculos = _crear_actores()
    contenedores, sensores = _crear_contenedores_y_sensores()
    _crear_reglas(usuarios[0])
    envio = _crear_envio(cliente, contenedores)
    _crear_tramos(envio, vehiculos, operadores, salida)
    _cargar_lecturas(sensores, salida)
    _crear_eventos_e_incidentes(envio, salida)
    _crear_prediccion(envio)
    _crear_facturacion(cliente, proveedor, operadores)
    _crear_mensajeria_y_reporte(usuarios)

    print(
        f"Envío de ejemplo creado: id {envio.id_envio} ({envio.origen} -> {envio.destino}), "
        f"3 tramos, {len(contenedores)} contenedores, {len(contenedores) * 4} sensores."
    )
    print(f"Abrilo en la UI: /envio?id_envio={envio.id_envio}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--solo-limpiar", action="store_true", help="Solo borra el ejemplo, no lo vuelve a cargar")
    args = parser.parse_args()

    setup_logging()
    try:
        if args.solo_limpiar:
            _limpiar_ejemplo_anterior()
        else:
            cargar_ejemplo()
    except AppError as e:
        print(f"Error: {e}")
        raise


if __name__ == "__main__":
    main()
