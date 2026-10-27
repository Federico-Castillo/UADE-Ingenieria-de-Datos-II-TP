"""Menú de Mensaje (MongoDB): chat privado y grupal."""
from app.cli.io_utils import leer_entero, leer_no_vacio, leer_opcion, pausar
from app.core.exceptions import AppError
from app.domain.mensaje import Mensaje
from app.services.mensaje_service import MensajeService


def _imprimir(m: Mensaje) -> None:
    destino = f"-> usuario {m.id_destinatario}" if m.id_destinatario else f"-> grupo {m.id_grupo}"
    print(f"  [{m.id_mensaje}] de {m.id_remitente} {destino} | {m.fecha_hora}\n      {m.contenido}")


def _enviar_privado(service: MensajeService) -> None:
    print("\n-- Enviar Mensaje Privado --")
    mensaje = Mensaje(
        id_remitente=leer_entero("ID de usuario remitente"),
        id_destinatario=leer_entero("ID de usuario destinatario"),
        contenido=leer_no_vacio("Contenido"),
        tipo="privado",
    )
    creado = service.enviar(mensaje)
    print(f"Mensaje enviado con id {creado.id_mensaje}.")


def _enviar_grupal(service: MensajeService) -> None:
    print("\n-- Enviar Mensaje Grupal --")
    mensaje = Mensaje(
        id_remitente=leer_entero("ID de usuario remitente"),
        id_grupo=leer_no_vacio("ID de grupo"),
        contenido=leer_no_vacio("Contenido"),
        tipo="grupal",
    )
    creado = service.enviar(mensaje)
    print(f"Mensaje enviado con id {creado.id_mensaje}.")


def _ver_conversacion_privada(service: MensajeService) -> None:
    print("\n-- Conversación Privada --")
    id_a = leer_entero("ID de usuario A")
    id_b = leer_entero("ID de usuario B")
    mensajes = service.listar_conversacion_privada(id_a, id_b)
    if not mensajes:
        print("  No hay mensajes entre esos usuarios.")
    for m in mensajes:
        _imprimir(m)


def _ver_conversacion_grupal(service: MensajeService) -> None:
    print("\n-- Conversación Grupal --")
    id_grupo = leer_no_vacio("ID de grupo")
    mensajes = service.listar_de_grupo(id_grupo)
    if not mensajes:
        print("  Ese grupo no tiene mensajes.")
    for m in mensajes:
        _imprimir(m)


_ACCIONES = {
    "1": ("Enviar mensaje privado", _enviar_privado),
    "2": ("Enviar mensaje grupal", _enviar_grupal),
    "3": ("Ver conversación privada", _ver_conversacion_privada),
    "4": ("Ver conversación grupal", _ver_conversacion_grupal),
}


def menu_mensaje() -> None:
    service = MensajeService()
    while True:
        print("\n=== Mensajería (MongoDB) ===")
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
