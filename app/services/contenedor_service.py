from app.core.exceptions import NotFoundError, ValidationError
from app.domain.contenedor import Contenedor
from app.repositories.contenedor_repository import ContenedorRepository


class ContenedorService:
    def __init__(self, repository: ContenedorRepository | None = None):
        self._repo = repository or ContenedorRepository()

    def _validar(self, contenedor: Contenedor) -> None:
        if not contenedor.codigo_internacional or not contenedor.codigo_internacional.strip():
            raise ValidationError("El código internacional no puede estar vacío.")
        if not contenedor.tipo or not contenedor.tipo.strip():
            raise ValidationError("El tipo no puede estar vacío.")
        if contenedor.capacidad <= 0:
            raise ValidationError("La capacidad debe ser mayor a cero.")

    def dar_alta(self, contenedor: Contenedor) -> Contenedor:
        self._validar(contenedor)
        if self._repo.obtener_por_codigo(contenedor.codigo_internacional) is not None:
            raise ValidationError(
                f"Ya existe un contenedor con el código {contenedor.codigo_internacional}."
            )
        id_contenedor = self._repo.crear(contenedor)
        contenedor.id_contenedor = id_contenedor
        return contenedor

    def modificar(self, contenedor: Contenedor) -> None:
        if contenedor.id_contenedor is None:
            raise ValidationError("No se puede modificar un contenedor sin id_contenedor.")
        self._validar(contenedor)
        if self._repo.obtener_por_id(contenedor.id_contenedor) is None:
            raise NotFoundError(f"No existe un contenedor con id {contenedor.id_contenedor}.")
        self._repo.actualizar(contenedor)

    def eliminar(self, id_contenedor: int) -> None:
        if self._repo.obtener_por_id(id_contenedor) is None:
            raise NotFoundError(f"No existe un contenedor con id {id_contenedor}.")
        self._repo.eliminar(id_contenedor)

    def obtener_por_id(self, id_contenedor: int) -> Contenedor:
        contenedor = self._repo.obtener_por_id(id_contenedor)
        if contenedor is None:
            raise NotFoundError(f"No existe un contenedor con id {id_contenedor}.")
        return contenedor

    def listar(self) -> list[Contenedor]:
        return self._repo.listar()

    def buscar(self, texto: str) -> list[Contenedor]:
        if not texto or not texto.strip():
            raise ValidationError("El texto de búsqueda no puede estar vacío.")
        return self._repo.buscar(texto)
