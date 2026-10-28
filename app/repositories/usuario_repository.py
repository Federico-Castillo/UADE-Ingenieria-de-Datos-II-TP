"""Acceso a datos de Usuario contra MySQL (SQL parametrizado, sin ORM)."""
import logging

from mysql.connector import Error as MySQLError

from app.core.exceptions import DuplicateError, RepositoryError
from app.db.mysql import get_cursor, transaction
from app.domain.usuario import Usuario

logger = logging.getLogger(__name__)

_MYSQL_DUPLICATE_ENTRY = 1062


def _row_to_usuario(row: dict) -> Usuario:
    return Usuario(
        id_usuario=row["id_usuario"],
        id_cliente=row["id_cliente"],
        id_rol=row["id_rol"],
        nombre=row["nombre"],
        apellido=row["apellido"],
        email=row["email"],
        password_hash=row["password_hash"],
        estado=row["estado"],
        fecha_registro=row["fecha_registro"],
    )


class UsuarioRepository:
    def crear(self, usuario: Usuario) -> int:
        try:
            with transaction() as cursor:
                cursor.execute(
                    """
                    INSERT INTO usuario
                        (id_cliente, id_rol, nombre, apellido, email, password_hash, estado)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        usuario.id_cliente,
                        usuario.id_rol,
                        usuario.nombre,
                        usuario.apellido,
                        usuario.email,
                        usuario.password_hash,
                        usuario.estado,
                    ),
                )
                id_usuario = cursor.lastrowid
                logger.info("Usuario creado id=%s", id_usuario)
                return id_usuario
        except MySQLError as e:
            if e.errno == _MYSQL_DUPLICATE_ENTRY:
                logger.warning("Alta de usuario duplicada: %s", e)
                raise DuplicateError(f"Ya existe un usuario con el email {usuario.email}.") from e
            logger.exception("Error creando usuario")
            raise RepositoryError(f"No se pudo crear el usuario: {e}") from e

    def obtener_por_id(self, id_usuario: int) -> Usuario | None:
        try:
            with get_cursor() as cursor:
                cursor.execute("SELECT * FROM usuario WHERE id_usuario = %s", (id_usuario,))
                row = cursor.fetchone()
                return _row_to_usuario(row) if row else None
        except MySQLError as e:
            logger.exception("Error obteniendo usuario por id")
            raise RepositoryError(f"No se pudo obtener el usuario: {e}") from e

    def obtener_por_email(self, email: str) -> Usuario | None:
        try:
            with get_cursor() as cursor:
                cursor.execute("SELECT * FROM usuario WHERE email = %s", (email,))
                row = cursor.fetchone()
                return _row_to_usuario(row) if row else None
        except MySQLError as e:
            logger.exception("Error obteniendo usuario por email")
            raise RepositoryError(f"No se pudo obtener el usuario: {e}") from e

    def listar(self, solo_activos: bool = False) -> list[Usuario]:
        try:
            with get_cursor() as cursor:
                if solo_activos:
                    cursor.execute("SELECT * FROM usuario WHERE estado = 'activo' ORDER BY apellido, nombre")
                else:
                    cursor.execute("SELECT * FROM usuario ORDER BY apellido, nombre")
                return [_row_to_usuario(row) for row in cursor.fetchall()]
        except MySQLError as e:
            logger.exception("Error listando usuarios")
            raise RepositoryError(f"No se pudo listar los usuarios: {e}") from e

    def buscar(self, texto: str) -> list[Usuario]:
        try:
            with get_cursor() as cursor:
                patron = f"%{texto}%"
                cursor.execute(
                    """
                    SELECT * FROM usuario
                    WHERE nombre LIKE %s OR apellido LIKE %s OR email LIKE %s
                    ORDER BY apellido, nombre
                    """,
                    (patron, patron, patron),
                )
                return [_row_to_usuario(row) for row in cursor.fetchall()]
        except MySQLError as e:
            logger.exception("Error buscando usuarios")
            raise RepositoryError(f"No se pudo buscar usuarios: {e}") from e

    def actualizar(self, usuario: Usuario) -> None:
        try:
            with transaction() as cursor:
                cursor.execute(
                    """
                    UPDATE usuario
                    SET id_cliente = %s, id_rol = %s, nombre = %s, apellido = %s,
                        email = %s, password_hash = %s, estado = %s
                    WHERE id_usuario = %s
                    """,
                    (
                        usuario.id_cliente,
                        usuario.id_rol,
                        usuario.nombre,
                        usuario.apellido,
                        usuario.email,
                        usuario.password_hash,
                        usuario.estado,
                        usuario.id_usuario,
                    ),
                )
            logger.info("Usuario actualizado id=%s", usuario.id_usuario)
        except MySQLError as e:
            if e.errno == _MYSQL_DUPLICATE_ENTRY:
                logger.warning("Actualización de usuario duplicada: %s", e)
                raise DuplicateError(f"Ya existe otro usuario con el email {usuario.email}.") from e
            logger.exception("Error actualizando usuario")
            raise RepositoryError(f"No se pudo actualizar el usuario: {e}") from e

    def eliminar(self, id_usuario: int) -> None:
        """Baja lógica (preserva trazabilidad de reportes/reglas creados por el usuario)."""
        try:
            with transaction() as cursor:
                cursor.execute(
                    "UPDATE usuario SET estado = 'inactivo' WHERE id_usuario = %s",
                    (id_usuario,),
                )
            logger.info("Usuario dado de baja id=%s", id_usuario)
        except MySQLError as e:
            logger.exception("Error dando de baja usuario")
            raise RepositoryError(f"No se pudo dar de baja el usuario: {e}") from e
