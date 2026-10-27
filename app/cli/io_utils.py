"""Helpers de entrada/salida para los menús de consola."""
import getpass


def leer_password(etiqueta: str = "Contraseña") -> str:
    return getpass.getpass(f"{etiqueta}: ")


def leer_no_vacio(etiqueta: str) -> str:
    while True:
        valor = input(f"{etiqueta}: ").strip()
        if valor:
            return valor
        print("  Este campo es obligatorio.")


def leer_opcional(etiqueta: str) -> str | None:
    valor = input(f"{etiqueta} (opcional): ").strip()
    return valor or None


def leer_opcion(etiqueta: str, opciones_validas: set[str]) -> str:
    while True:
        valor = input(f"{etiqueta}: ").strip()
        if valor in opciones_validas:
            return valor
        print(f"  Opción inválida. Elegí una de: {', '.join(sorted(opciones_validas))}")


def leer_entero(etiqueta: str) -> int:
    while True:
        valor = input(f"{etiqueta}: ").strip()
        if valor.isdigit():
            return int(valor)
        print("  Ingresá un número entero válido.")


def confirmar(mensaje: str) -> bool:
    valor = input(f"{mensaje} (s/n): ").strip().lower()
    return valor == "s"


def pausar() -> None:
    input("\nPresioná Enter para continuar...")
