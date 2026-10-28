"""Verificación inicial de importación; las pruebas de búsqueda están pendientes."""

from importlib import import_module


def test_modulos_importables():
    """Comprueba que pytest puede importar la estructura base del proyecto."""
    nombres = (
        "motor_ast",
        "motor_ast.extractor",
        "motor_ast.normalizador",
        "motor_ast.serializador",
        "motor_ast.similitud",
        "motor_ast.buscador",
        "buscar_similares",
    )
    for nombre in nombres:
        modulo = import_module(nombre)
        assert modulo.__name__ == nombre
