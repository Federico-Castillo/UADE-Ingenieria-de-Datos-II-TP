from dataclasses import dataclass, field


@dataclass
class GrupoTrabajo:
    nombre: str
    integrantes: list[int] = field(default_factory=list)
    id_grupo: str | None = None
