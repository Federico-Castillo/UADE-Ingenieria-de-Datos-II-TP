"""Acceso a datos de Cliente contra MySQL (SQL parametrizado, sin ORM)."""
import logging

from mysql.connector import Error as MySQLError

from app.core.exceptions import DuplicateError, RepositoryError
from app.db.mysql import get_cursor, transaction
from app.domain.cliente import Cliente

logger = logging.getLogger(__name__)

_MYSQL_DUPLICATE_ENTRY = 1062


def _row_to_cliente(row: dict) -> Cliente:
    return Cliente(
        id_cliente=row["id_cliente"],
        razon_social=row["razon_social"],
        cuit=row["cuit"],
        email=row["email"],
        telefono=row["telefono"],
        direccion=row["direccion"],
        pais=row["pais"],
        estado=row["estado"],
    )


class ClienteRepository:
    def crear(self, cliente: Cliente) -> int:
        try:
            with transaction() as cursor:
                cursor.execute(
                    """
                    INSERT INTO cliente
                        (razon_social, cuit, email, telefono, direccion, pais, estado)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        cliente.razon_social,
                        cliente.cuit,
                        cliente.email,
                        cliente.telefono,
                        cliente.direccion,
                        cliente.pais,
                        cliente.estado,
                    ),
                )
                return cursor.lastrowid
        except MySQLError as e:
            if e.errno == _MYSQL_DUPLICATE_ENTRY:
                logger.warning("Alta de cliente duplicada: %s", e)
                raise DuplicateError(
                    f"Ya existe un cliente con ese CUIT o email ({cliente.cuit} / {cliente.email})."
                ) from e
            logger.exception("Error creando cliente")
            raise RepositoryError(f"No se pudo crear el cliente: {e}") from e

    def obtener_por_id(self, id_cliente: int) -> Cliente | None:
        try:
            with get_cursor() as cursor:
                cursor.execute("SELECT * FROM cliente WHERE id_cliente = %s", (id_cliente,))
                row = cursor.fetchone()
                return _row_to_cliente(row) if row else None
        except MySQLError as e:
            logger.exception("Error obteniendo cliente por id")
            raise RepositoryError(f"No se pudo obtener el cliente: {e}") from e

    def obtener_por_cuit(self, cuit: str) -> Cliente | None:
        try:
            with get_cursor() as cursor:
                cursor.execute("SELECT * FROM cliente WHERE cuit = %s", (cuit,))
                row = cursor.fetchone()
                return _row_to_cliente(row) if row else None
        except MySQLError as e:
            logger.exception("Error obteniendo cliente por CUIT")
            raise RepositoryError(f"No se pudo obtener el cliente: {e}") from e

    def obtener_por_email(self, email: str) -> Cliente | None:
        try:
            with get_cursor() as cursor:
                cursor.execute("SELECT * FROM cliente WHERE email = %s", (email,))
                row = cursor.fetchone()
                return _row_to_cliente(row) if row else None
        except MySQLError as e:
            logger.exception("Error obteniendo cliente por email")
            raise RepositoryError(f"No se pudo obtener el cliente: {e}") from e

    def listar(self, solo_activos: bool = False) -> list[Cliente]:
        try:
            with get_cursor() as cursor:
                if solo_activos:
                    cursor.execute("SELECT * FROM cliente WHERE estado = 'activo' ORDER BY razon_social")
                else:
                    cursor.execute("SELECT * FROM cliente ORDER BY razon_social")
                return [_row_to_cliente(row) for row in cursor.fetchall()]
        except MySQLError as e:
            logger.exception("Error listando clientes")
            raise RepositoryError(f"No se pudo listar los clientes: {e}") from e

    def buscar(self, texto: str) -> list[Cliente]:
        try:
            with get_cursor() as cursor:
                patron = f"%{texto}%"
                cursor.execute(
                    "SELECT * FROM cliente WHERE razon_social LIKE %s OR cuit LIKE %s ORDER BY razon_social",
                    (patron, patron),
                )
                return [_row_to_cliente(row) for row in cursor.fetchall()]
        except MySQLError as e:
            logger.exception("Error buscando clientes")
            raise RepositoryError(f"No se pudo buscar clientes: {e}") from e

    def actualizar(self, cliente: Cliente) -> None:
        try:
            with transaction() as cursor:
                cursor.execute(
                    """
                    UPDATE cliente
                    SET razon_social = %s, cuit = %s, email = %s, telefono = %s,
                        direccion = %s, pais = %s, estado = %s
                    WHERE id_cliente = %s
                    """,
                    (
                        cliente.razon_social,
                        cliente.cuit,
                        cliente.email,
                        cliente.telefono,
                        cliente.direccion,
                        cliente.pais,
                        cliente.estado,
                        cliente.id_cliente,
                    ),
                )
        except MySQLError as e:
            if e.errno == _MYSQL_DUPLICATE_ENTRY:
                logger.warning("Actualización de cliente duplicada: %s", e)
                raise DuplicateError(
                    f"Ya existe otro cliente con ese CUIT o email ({cliente.cuit} / {cliente.email})."
                ) from e
            logger.exception("Error actualizando cliente")
            raise RepositoryError(f"No se pudo actualizar el cliente: {e}") from e

    def eliminar(self, id_cliente: int) -> None:
        """Baja lógica: el cliente nunca se borra físicamente (preserva
        trazabilidad de envíos/facturas asociadas, consistente con los
        FOREIGN KEY ... ON DELETE RESTRICT del esquema)."""
        try:
            with transaction() as cursor:
                cursor.execute(
                    "UPDATE cliente SET estado = 'inactivo' WHERE id_cliente = %s",
                    (id_cliente,),
                )
        except MySQLError as e:
            logger.exception("Error dando de baja cliente")
            raise RepositoryError(f"No se pudo dar de baja el cliente: {e}") from e
