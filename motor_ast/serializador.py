"""Serializa ASTs normalizados en secuencias de tokens mediante recorrido pre-order.

Convierte el subárbol AST de una función en una lista lineal de tokens
determinista, preservando la estructura sintáctica, los operadores, los
identificadores normalizados (VAR1, VAR2, ...) y los literales (LIT).

Uso principal:
    tokens = serializar_ast(ast_normalizado)

Flujo del motor:
    extractor -> normalizador -> serializador -> (similitud / buscador)

Para ver una demostración desde la raíz del proyecto:
    python -m motor_ast.serializador
"""

import ast


def _token_de_nodo(nodo: ast.AST) -> str:
    """Devuelve la representación en token de un nodo AST individual.

    Para nodos con identificadores y literales normalizados relevantes (Name,
    arg, Constant), incorpora su valor al token (por ejemplo 'Name:VAR1',
    'arg:VAR2', 'Constant:LIT'). Para FunctionDef y AsyncFunctionDef se emite
    únicamente el tipo de nodo para no introducir el nombre de la función en la
    comparación. Para el resto de los nodos, se devuelve el nombre del tipo AST
    (por ejemplo 'BinOp', 'Add', 'Return', 'If', 'For', 'While').
    """
    if isinstance(nodo, ast.Name):
        return f"Name:{nodo.id}"
    if isinstance(nodo, ast.arg):
        return f"arg:{nodo.arg}"
    if isinstance(nodo, ast.Constant):
        return f"Constant:{nodo.value}"
    return type(nodo).__name__


def serializar_ast(nodo: ast.AST) -> list[str]:
    """Convierte un nodo AST en una secuencia lineal de tokens en orden pre-order.

    Algoritmo pre-order:
        1. Se registra el token del nodo actual (raíz del subárbol).
        2. Se recorren recursivamente sus nodos hijos en orden mediante
           ast.iter_child_nodes().

    No modifica el AST recibido ni depende de la ubicación del archivo ni de
    números de línea.

    Lanza TypeError si el argumento no es una instancia de ast.AST.
    """
    if not isinstance(nodo, ast.AST):
        raise TypeError(f"Se esperaba un nodo ast.AST, pero se recibió {type(nodo).__name__}")

    tokens: list[str] = [_token_de_nodo(nodo)]
    for hijo in ast.iter_child_nodes(nodo):
        tokens.extend(serializar_ast(hijo))
    return tokens


def _demostrar_serializacion() -> None:
    """Extrae ejemplos reales, normaliza y serializa sus AST mostrando la secuencia."""
    from pathlib import Path

    from motor_ast.extractor import extraer_funciones_directorio
    from motor_ast.normalizador import normalizar_ast

    directorio = Path(__file__).resolve().parent.parent / "ejemplos"
    funciones = extraer_funciones_directorio(directorio)

    secuencias: dict[str, list[str]] = {}

    for funcion in funciones:
        normalizado = normalizar_ast(funcion.nodo_ast)
        tokens = serializar_ast(normalizado)
        secuencias[funcion.nombre] = tokens

        print("=" * 60)
        print(f"Archivo: {funcion.archivo.name} | Función: {funcion.nombre}")
        print("-" * 60)
        print("1. Código original:")
        print(ast.unparse(funcion.nodo_ast))
        print("\n2. AST normalizado:")
        print(ast.dump(normalizado, indent=4, include_attributes=False))
        print("\n3. Secuencia de tokens pre-order:")
        print(tokens)
        print(f"\n4. Cantidad de tokens generados: {len(tokens)}")

    print("\n" + "=" * 60)
    print("Comprobación de equivalencia entre funciones:")
    if "sumar_elementos" in secuencias and "acumular_valores" in secuencias:
        iguales = secuencias["sumar_elementos"] == secuencias["acumular_valores"]
        print(
            f"- 'sumar_elementos' vs 'acumular_valores': "
            f"{'IDÉNTICAS' if iguales else 'DISTINTAS'} (esperado: IDÉNTICAS)"
        )
    if "es_par" in secuencias and "sumar_elementos" in secuencias:
        distintas = secuencias["es_par"] != secuencias["sumar_elementos"]
        print(
            f"- 'es_par' vs 'sumar_elementos': "
            f"{'DISTINTAS' if distintas else 'IDÉNTICAS'} (esperado: DISTINTAS)"
        )
    print("=" * 60)


if __name__ == "__main__":
    _demostrar_serializacion()
