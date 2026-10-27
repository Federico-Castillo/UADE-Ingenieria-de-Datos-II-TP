class AppError(Exception):
    """Raíz de toda excepción propia de la aplicación."""


class RepositoryError(AppError):
    """Error de infraestructura/driver traducido por la capa de repositorio."""


class NotFoundError(AppError):
    """La entidad solicitada no existe."""


class DuplicateError(AppError):
    """La operación viola una restricción de unicidad del dominio."""


class ValidationError(AppError):
    """Un dato no cumple una regla de negocio antes de llegar a la base."""


class ConnectionConfigError(AppError):
    """Falta configuración obligatoria o falló la conexión a un motor al iniciar."""
