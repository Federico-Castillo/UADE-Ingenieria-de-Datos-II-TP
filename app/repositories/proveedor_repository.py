"""Acceso a datos de Proveedor contra MySQL (SQL parametrizado, sin ORM)."""
import logging

from mysql.connector import Error as MySQLError

from app.core.exceptions import DuplicateError, RepositoryError
from app.db.mysql import get_cursor, transaction
from app.domain.proveedor import Proveedor

logger = logging.getLogger(__name__)

_MYSQL_DUPLICATE_ENTRY = 1062


def _row_to_proveedor(row: dict) -> Proveedor:
    return Proveedor(
        id_proveedor=row["id_proveedor"],
        razon_social=row["razon_social"],
        cuit=row["cuit"],
        email=row["email"],
        telefono=row["telefono"],
        direccion=row["direccion"],
        pais=row["pais"],
        estado=row["estado"],
    )


class ProveedorRepository:
    def crear(self, proveedor: Proveedor) -> int:
        try:
            with transaction() as cursor:
                cursor.execute(
                    """
                    INSERT INTO proveedor
                        (razon_social, cuit, email, telefono, direccion, pais, estado)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        proveedor.razon_social,
                        proveedor.cuit,
                        proveedor.email,
                        proveedor.telefono,
                        proveedor.direccion,
                        proveedor.pais,
                        proveedor.estado,
                    ),
                )
                return cursor.lastrowid
        except MySQLError as e:
            if e.errno == _MYSQL_DUPLICATE_ENTRY:
                logger.warning("Alta de proveedor duplicada: %s", e)
                raise DuplicateError(
                    f"Ya existe un proveedor con ese CUIT o email ({proveedor.cuit} / {proveedor.email})."
                ) from e
            logger.exception("Error creando proveedor")
            raise RepositoryError(f"No se pudo crear el proveedor: {e}") from e

    def obtener_por_id(self, id_proveedor: int) -> Proveedor | None:
        try:
            with get_cursor() as cursor:
                cursor.execute("SELECT * FROM proveedor WHERE id_proveedor = %s", (id_proveedor,))
                row = cursor.fetchone()
                return _row_to_proveedor(row) if row else None
        except MySQLError as e:
            logger.exception("Error obteniendo proveedor por id")
            raise RepositoryError(f"No se pudo obtener el proveedor: {e}") from e

    def obtener_por_cuit(self, cuit: str) -> Proveedor | None:
        try:
            with get_cursor() as cursor:
                cursor.execute("SELECT * FROM proveedor WHERE cuit = %s", (cuit,))
                row = cursor.fetchone()
                return _row_to_proveedor(row) if row else None
        except MySQLError as e:
            logger.exception("Error obteniendo proveedor por CUIT")
            raise RepositoryError(f"No se pudo obtener el proveedor: {e}") from e

    def obtener_por_email(self, email: str) -> Proveedor | None:
        try:
            with get_cursor() as cursor:
                cursor.execute("SELECT * FROM proveedor WHERE email = %s", (email,))
                row = cursor.fetchone()
                return _row_to_proveedor(row) if row else None
        except MySQLError as e:
            logger.exception("Error obteniendo proveedor por email")
            raise RepositoryError(f"No se pudo obtener el proveedor: {e}") from e

    def listar(self, solo_activos: bool = False) -> list[Proveedor]:
        try:
            with get_cursor() as cursor:
                if solo_activos:
                    cursor.execute("SELECT * FROM proveedor WHERE estado = 'activo' ORDER BY razon_social")
                else:
                    cursor.execute("SELECT * FROM proveedor ORDER BY razon_social")
                return [_row_to_proveedor(row) for row in cursor.fetchall()]
        except MySQLError as e:
            logger.exception("Error listando proveedores")
            raise RepositoryError(f"No se pudo listar los proveedores: {e}") from e

    def buscar(self, texto: str) -> list[Proveedor]:
        try:
            with get_cursor() as cursor:
                patron = f"%{texto}%"
                cursor.execute(
                    "SELECT * FROM proveedor WHERE razon_social LIKE %s OR cuit LIKE %s ORDER BY razon_social",
                    (patron, patron),
                )
                return [_row_to_proveedor(row) for row in cursor.fetchall()]
        except MySQLError as e:
            logger.exception("Error buscando proveedores")
            raise RepositoryError(f"No se pudo buscar proveedores: {e}") from e

    def actualizar(self, proveedor: Proveedor) -> None:
        try:
            with transaction() as cursor:
                cursor.execute(
                    """
                    UPDATE proveedor
                    SET razon_social = %s, cuit = %s, email = %s, telefono = %s,
                        direccion = %s, pais = %s, estado = %s
                    WHERE id_proveedor = %s
                    """,
                    (
                        proveedor.razon_social,
                        proveedor.cuit,
                        proveedor.email,
                        proveedor.telefono,
                        proveedor.direccion,
                        proveedor.pais,
                        proveedor.estado,
                        proveedor.id_proveedor,
                    ),
                )
        except MySQLError as e:
            if e.errno == _MYSQL_DUPLICATE_ENTRY:
                logger.warning("Actualización de proveedor duplicada: %s", e)
                raise DuplicateError(
                    f"Ya existe otro proveedor con ese CUIT o email ({proveedor.cuit} / {proveedor.email})."
                ) from e
            logger.exception("Error actualizando proveedor")
            raise RepositoryError(f"No se pudo actualizar el proveedor: {e}") from e

    def eliminar(self, id_proveedor: int) -> None:
        """Baja lógica, igual que Cliente (preserva trazabilidad de facturas
        recibidas asociadas)."""
        try:
            with transaction() as cursor:
                cursor.execute(
                    "UPDATE proveedor SET estado = 'inactivo' WHERE id_proveedor = %s",
                    (id_proveedor,),
                )
        except MySQLError as e:
            logger.exception("Error dando de baja proveedor")
            raise RepositoryError(f"No se pudo dar de baja el proveedor: {e}") from e
