"""Acceso a datos de OperadorLogistico contra MySQL (SQL parametrizado, sin ORM)."""
import logging

from mysql.connector import Error as MySQLError

from app.core.exceptions import DuplicateError, RepositoryError
from app.db.mysql import get_cursor, transaction
from app.domain.operador_logistico import OperadorLogistico

logger = logging.getLogger(__name__)

_MYSQL_DUPLICATE_ENTRY = 1062


def _row_to_operador(row: dict) -> OperadorLogistico:
    return OperadorLogistico(
        id_operador_logistico=row["id_operador_logistico"],
        razon_social=row["razon_social"],
        cuit=row["cuit"],
        email=row["email"],
        telefono=row["telefono"],
        estado=row["estado"],
    )


class OperadorLogisticoRepository:
    def crear(self, operador: OperadorLogistico) -> int:
        try:
            with transaction() as cursor:
                cursor.execute(
                    """
                    INSERT INTO operador_logistico (razon_social, cuit, email, telefono, estado)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (operador.razon_social, operador.cuit, operador.email, operador.telefono, operador.estado),
                )
                id_operador_logistico = cursor.lastrowid
                logger.info("Operador logístico creado id=%s", id_operador_logistico)
                return id_operador_logistico
        except MySQLError as e:
            if e.errno == _MYSQL_DUPLICATE_ENTRY:
                logger.warning("Alta de operador logístico duplicada: %s", e)
                raise DuplicateError(
                    f"Ya existe un operador logístico con ese CUIT o email ({operador.cuit} / {operador.email})."
                ) from e
            logger.exception("Error creando operador logístico")
            raise RepositoryError(f"No se pudo crear el operador logístico: {e}") from e

    def obtener_por_id(self, id_operador_logistico: int) -> OperadorLogistico | None:
        try:
            with get_cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM operador_logistico WHERE id_operador_logistico = %s",
                    (id_operador_logistico,),
                )
                row = cursor.fetchone()
                return _row_to_operador(row) if row else None
        except MySQLError as e:
            logger.exception("Error obteniendo operador logístico por id")
            raise RepositoryError(f"No se pudo obtener el operador logístico: {e}") from e

    def obtener_por_cuit(self, cuit: str) -> OperadorLogistico | None:
        try:
            with get_cursor() as cursor:
                cursor.execute("SELECT * FROM operador_logistico WHERE cuit = %s", (cuit,))
                row = cursor.fetchone()
                return _row_to_operador(row) if row else None
        except MySQLError as e:
            logger.exception("Error obteniendo operador logístico por CUIT")
            raise RepositoryError(f"No se pudo obtener el operador logístico: {e}") from e

    def obtener_por_email(self, email: str) -> OperadorLogistico | None:
        try:
            with get_cursor() as cursor:
                cursor.execute("SELECT * FROM operador_logistico WHERE email = %s", (email,))
                row = cursor.fetchone()
                return _row_to_operador(row) if row else None
        except MySQLError as e:
            logger.exception("Error obteniendo operador logístico por email")
            raise RepositoryError(f"No se pudo obtener el operador logístico: {e}") from e

    def listar(self, solo_activos: bool = False) -> list[OperadorLogistico]:
        try:
            with get_cursor() as cursor:
                if solo_activos:
                    cursor.execute(
                        "SELECT * FROM operador_logistico WHERE estado = 'activo' ORDER BY razon_social"
                    )
                else:
                    cursor.execute("SELECT * FROM operador_logistico ORDER BY razon_social")
                return [_row_to_operador(row) for row in cursor.fetchall()]
        except MySQLError as e:
            logger.exception("Error listando operadores logísticos")
            raise RepositoryError(f"No se pudo listar los operadores logísticos: {e}") from e

    def buscar(self, texto: str) -> list[OperadorLogistico]:
        try:
            with get_cursor() as cursor:
                patron = f"%{texto}%"
                cursor.execute(
                    "SELECT * FROM operador_logistico WHERE razon_social LIKE %s OR cuit LIKE %s ORDER BY razon_social",
                    (patron, patron),
                )
                return [_row_to_operador(row) for row in cursor.fetchall()]
        except MySQLError as e:
            logger.exception("Error buscando operadores logísticos")
            raise RepositoryError(f"No se pudo buscar operadores logísticos: {e}") from e

    def actualizar(self, operador: OperadorLogistico) -> None:
        try:
            with transaction() as cursor:
                cursor.execute(
                    """
                    UPDATE operador_logistico
                    SET razon_social = %s, cuit = %s, email = %s, telefono = %s, estado = %s
                    WHERE id_operador_logistico = %s
                    """,
                    (
                        operador.razon_social,
                        operador.cuit,
                        operador.email,
                        operador.telefono,
                        operador.estado,
                        operador.id_operador_logistico,
                    ),
                )
            logger.info("Operador logístico actualizado id=%s", operador.id_operador_logistico)
        except MySQLError as e:
            if e.errno == _MYSQL_DUPLICATE_ENTRY:
                logger.warning("Actualización de operador logístico duplicada: %s", e)
                raise DuplicateError(
                    f"Ya existe otro operador logístico con ese CUIT o email "
                    f"({operador.cuit} / {operador.email})."
                ) from e
            logger.exception("Error actualizando operador logístico")
            raise RepositoryError(f"No se pudo actualizar el operador logístico: {e}") from e

    def eliminar(self, id_operador_logistico: int) -> None:
        """Baja lógica, igual que Cliente/Proveedor."""
        try:
            with transaction() as cursor:
                cursor.execute(
                    "UPDATE operador_logistico SET estado = 'inactivo' WHERE id_operador_logistico = %s",
                    (id_operador_logistico,),
                )
            logger.info("Operador logístico dado de baja id=%s", id_operador_logistico)
        except MySQLError as e:
            logger.exception("Error dando de baja operador logístico")
            raise RepositoryError(f"No se pudo dar de baja el operador logístico: {e}") from e
