"""Funciones equivalentes con nombres diferentes para futuras comparaciones."""


def sumar_elementos(numeros: list[int]) -> int:
    """Suma los números mediante un acumulador."""
    total = 0
    for numero in numeros:
        total += numero
    return total


def acumular_valores(valores: list[int]) -> int:
    """Suma los valores mediante un acumulador."""
    resultado = 0
    for valor in valores:
        resultado += valor
    return resultado
