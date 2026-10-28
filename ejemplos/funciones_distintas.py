"""Funciones con estructuras diferentes para futuras comparaciones."""


def es_par(numero: int) -> bool:
    """Indica si el número es divisible por dos."""
    return numero % 2 == 0


def calcular_factorial(numero: int) -> int:
    """Calcula el factorial de un entero no negativo mediante un bucle."""
    if numero < 0:
        raise ValueError("El número debe ser no negativo")
    resultado = 1
    for factor in range(2, numero + 1):
        resultado *= factor
    return resultado
