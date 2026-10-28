"""Menú ABM de Usuario."""
from app.cli.io_utils import confirmar, leer_entero, leer_no_vacio, leer_opcion, leer_password, limpiar_pantalla, pausar
from app.core.exceptions import AppError
from app.domain.usuario import Usuario
from app.services.rol_service import RolService
from app.services.usuario_service import UsuarioService


def _imprimir(u: Usuario) -> None:
    print(
        f"  [{u.id_usuario}] {u.nombre} {u.apellido} | {u.email} | rol {u.id_rol} | "
        f"cliente {u.id_cliente or '-'} | {u.estado}"
    )


def _mostrar_roles_disponibles() -> None:
    roles = RolService().listar()
    if roles:
        print("  Roles disponibles:")
        for r in roles:
            print(f"    [{r.id_rol}] {r.descripcion}")
    else:
        print("  No hay roles cargados todavía (Gestión de Roles).")


def _alta(service: UsuarioService) -> None:
    print("\n-- Alta de Usuario --")
    _mostrar_roles_disponibles()
    id_cliente_str = input("ID de cliente asociado (opcional): ").strip()
    usuario = Usuario(
        nombre=leer_no_vacio("Nombre"),
        apellido=leer_no_vacio("Apellido"),
        email=leer_no_vacio("Email"),
        id_rol=leer_entero("ID de rol"),
        id_cliente=int(id_cliente_str) if id_cliente_str.isdigit() else None,
    )
    password = leer_password("Contraseña (mínimo 6 caracteres)")
    creado = service.dar_alta(usuario, password)
    print(f"Usuario creado con id {creado.id_usuario}.")


def _baja(service: UsuarioService) -> None:
    print("\n-- Baja de Usuario --")
    id_usuario = leer_entero("ID de usuario a dar de baja")
    usuario = service.obtener_por_id(id_usuario)
    _imprimir(usuario)
    if confirmar("¿Confirmás la baja (lógica) de este usuario?"):
        service.dar_baja(id_usuario)
        print("Usuario dado de baja.")
    else:
        print("Operación cancelada.")


def _modificacion(service: UsuarioService) -> None:
    print("\n-- Modificación de Usuario --")
    id_usuario = leer_entero("ID de usuario a modificar")
    usuario = service.obtener_por_id(id_usuario)
    _imprimir(usuario)
    print("Dejá vacío para mantener el valor actual.")
    usuario.nombre = input(f"Nombre [{usuario.nombre}]: ").strip() or usuario.nombre
    usuario.apellido = input(f"Apellido [{usuario.apellido}]: ").strip() or usuario.apellido
    usuario.email = input(f"Email [{usuario.email}]: ").strip() or usuario.email
    rol_str = input(f"ID de rol [{usuario.id_rol}]: ").strip()
    usuario.id_rol = int(rol_str) if rol_str.isdigit() else usuario.id_rol
    if confirmar("¿Querés cambiar el estado?"):
        usuario.estado = leer_opcion(f"Estado [{usuario.estado}] (activo/inactivo)", {"activo", "inactivo"})
    service.modificar(usuario)
    print("Usuario modificado.")
    if confirmar("¿Querés cambiar la contraseña?"):
        nueva = leer_password("Nueva contraseña (mínimo 6 caracteres)")
        service.cambiar_password(usuario.id_usuario, nueva)
        print("Contraseña actualizada.")


def _listado(service: UsuarioService) -> None:
    print("\n-- Listado de Usuarios --")
    solo_activos = confirmar("¿Listar solo activos?")
    usuarios = service.listar(solo_activos=solo_activos)
    if not usuarios:
        print("  No hay usuarios para mostrar.")
    for u in usuarios:
        _imprimir(u)


def _busqueda(service: UsuarioService) -> None:
    print("\n-- Búsqueda de Usuarios --")
    texto = leer_no_vacio("Texto a buscar (nombre, apellido o email)")
    usuarios = service.buscar(texto)
    if not usuarios:
        print("  No se encontraron usuarios.")
    for u in usuarios:
        _imprimir(u)


_ACCIONES = {
    "1": ("Alta", _alta),
    "2": ("Baja", _baja),
    "3": ("Modificación", _modificacion),
    "4": ("Listado", _listado),
    "5": ("Búsqueda", _busqueda),
}


def menu_usuario() -> None:
    service = UsuarioService()
    while True:
        limpiar_pantalla()
        print("\n=== Gestión de Usuarios ===")
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
