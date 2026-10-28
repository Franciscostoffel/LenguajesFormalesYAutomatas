"""Extrae funciones Python y sus metadatos sin ejecutar ni transformar el código.

Al procesar un directorio, los archivos inválidos se omiten con una advertencia.
Los errores del directorio de entrada se propagan al llamador.
"""

import ast
from dataclasses import dataclass
import logging
from pathlib import Path
import tokenize


logger = logging.getLogger(__name__)


@dataclass
class FuncionExtraida:
    """Función y ubicación de origen; nodo_ast referencia el nodo original."""

    nombre: str
    archivo: Path
    linea: int
    nodo_ast: ast.FunctionDef | ast.AsyncFunctionDef


def encontrar_archivos_python(directorio: str | Path) -> list[Path]:
    """Lista archivos .py recursivamente, ordenados por ruta relativa.

    Lanza FileNotFoundError si la ruta no existe y NotADirectoryError si
    no es una carpeta. No aplica exclusiones de carpetas en esta etapa.
    """
    ruta = Path(directorio)
    if not ruta.exists():
        raise FileNotFoundError(f"El directorio no existe: {ruta}")
    if not ruta.is_dir():
        raise NotADirectoryError(f"La ruta no es un directorio: {ruta}")

    archivos = (archivo for archivo in ruta.rglob("*.py") if archivo.is_file())
    return sorted(archivos, key=lambda archivo: archivo.relative_to(ruta).as_posix())


def parsear_archivo(archivo: str | Path) -> ast.Module:
    """Lee un archivo respetando su codificación Python y construye su AST.

    Propaga OSError, UnicodeError o SyntaxError si no puede leer o parsear.
    El nombre del archivo se incluye en los errores de sintaxis.
    """
    ruta = Path(archivo)
    with tokenize.open(ruta) as fuente:
        codigo = fuente.read()
    return ast.parse(codigo, filename=str(ruta))


def extraer_funciones(arbol: ast.AST, archivo: str | Path) -> list[FuncionExtraida]:
    """Obtiene funciones, métodos y funciones anidadas, en orden de línea.

    Recorre todo el árbol con ast.walk() y conserva los nodos sin modificarlos.
    """
    ruta = Path(archivo)
    nodos = (
        nodo for nodo in ast.walk(arbol)
        if isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef))
    )
    return [
        FuncionExtraida(nodo.name, ruta, nodo.lineno, nodo)
        for nodo in sorted(nodos, key=lambda nodo: nodo.lineno)
    ]


def extraer_funciones_directorio(directorio: str | Path) -> list[FuncionExtraida]:
    """Extrae funciones de una carpeta y advierte sobre archivos omitidos.

    Continúa ante errores de lectura, codificación o sintaxis de cada archivo.
    Los errores de validación del directorio siguen propagándose al llamador.
    """
    funciones = []
    for archivo in encontrar_archivos_python(directorio):
        try:
            arbol = parsear_archivo(archivo)
        except (OSError, UnicodeError, SyntaxError) as error:
            logger.warning("Se omite el archivo %s: %s", archivo, error)
            continue
        funciones.extend(extraer_funciones(arbol, archivo))
    return funciones


def _demostrar_extraccion() -> None:
    """Muestra la extracción real de los archivos de ejemplos del proyecto."""
    directorio = Path(__file__).resolve().parent.parent / "ejemplos"
    try:
        funciones = extraer_funciones_directorio(directorio)
    except (OSError, UnicodeError, SyntaxError) as error:
        raise SystemExit(f"No se pudo completar la extracción: {error}") from error

    archivo_actual = None
    for indice, funcion in enumerate(funciones, start=1):
        if funcion.archivo != archivo_actual:
            archivo_actual = funcion.archivo
            print(f"\nArchivo: {funcion.archivo.relative_to(directorio.parent)}")
            print("Funciones encontradas:")
        print(f"\n{indice}. Nombre: {funcion.nombre}")
        print(f"   Línea: {funcion.linea}")
        print(f"   Tipo AST: {type(funcion.nodo_ast).__name__}")
    print(f"\nTotal de funciones encontradas: {len(funciones)}")


if __name__ == "__main__":
    _demostrar_extraccion()
