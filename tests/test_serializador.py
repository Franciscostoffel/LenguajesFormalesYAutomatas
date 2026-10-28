"""Pruebas de serialización pre-order y generación de secuencias de tokens."""

import ast
from pathlib import Path

import pytest

from motor_ast.extractor import extraer_funciones_directorio
from motor_ast.normalizador import normalizar_ast
from motor_ast.serializador import serializar_ast


def _obtener_funcion(codigo: str) -> ast.FunctionDef | ast.AsyncFunctionDef:
    """Extrae el primer nodo de función desde un fragmento de código."""
    return ast.parse(codigo).body[0]


def _serializar_codigo(codigo: str) -> list[str]:
    """Flujo estándar: código fuente -> AST -> normalizador -> serializador."""
    nodo = _obtener_funcion(codigo)
    normalizado = normalizar_ast(nodo)
    return serializar_ast(normalizado)


def test_serializacion_funcion_sencilla():
    """Verifica la secuencia exacta para una función de suma simple."""
    codigo = "def sumar(a, b):\n    return a + b\n"
    tokens = _serializar_codigo(codigo)

    secuencia_esperada = [
        "FunctionDef",
        "arguments",
        "arg:VAR1",
        "arg:VAR2",
        "Return",
        "BinOp",
        "Name:VAR1",
        "Load",
        "Add",
        "Name:VAR2",
        "Load",
    ]
    assert tokens == secuencia_esperada


def test_respeto_recorrido_pre_order_arbol_manual():
    """Comprueba el orden pre-order en un árbol pequeño verificable manualmente.

    Estructura manual:
            BinOp
           /  |  \\
     Constant Add Constant
      (LIT)         (LIT)

    En pre-order (raíz -> hijo izquierdo -> hijo central -> hijo derecho):
        1. BinOp
        2. Constant:LIT
        3. Add
        4. Constant:LIT
    """
    arbol_manual = ast.BinOp(
        left=ast.Constant(value="LIT"),
        op=ast.Add(),
        right=ast.Constant(value="LIT"),
    )
    tokens = serializar_ast(arbol_manual)
    assert tokens == ["BinOp", "Constant:LIT", "Add", "Constant:LIT"]


def test_conservacion_identificadores_normalizados():
    """Comprueba que los identificadores y parámetros normalizados figuren como tokens."""
    codigo = (
        "def calcular(precio, cantidad):\n"
        "    subtotal = precio * cantidad\n"
        "    return subtotal\n"
    )
    tokens = _serializar_codigo(codigo)

    assert "arg:VAR1" in tokens
    assert "arg:VAR2" in tokens
    assert "Name:VAR1" in tokens
    assert "Name:VAR2" in tokens
    assert "Name:VAR3" in tokens


def test_conservacion_tokens_lit_y_constantes():
    """Comprueba que los literales conserven su token 'Constant:LIT' y booleanos su valor."""
    codigo = (
        "def constantes():\n"
        "    cadena = 'texto'\n"
        "    numero = 42\n"
        "    flotante = 3.14\n"
        "    bandera = True\n"
        "    nulo = None\n"
        "    return cadena, numero, flotante, bandera, nulo\n"
    )
    tokens = _serializar_codigo(codigo)

    assert tokens.count("Constant:LIT") == 3
    assert "Constant:True" in tokens
    assert "Constant:None" in tokens


def test_preservacion_operadores_aritmeticos():
    """Comprueba que operadores distintos produzcan secuencias diferentes."""
    suma = _serializar_codigo("def f(a, b): return a + b")
    resta = _serializar_codigo("def f(a, b): return a - b")
    multiplicacion = _serializar_codigo("def f(a, b): return a * b")

    assert "Add" in suma and "Sub" not in suma and "Mult" not in suma
    assert "Sub" in resta and "Add" not in resta and "Mult" not in resta
    assert "Mult" in multiplicacion and "Add" not in multiplicacion and "Sub" not in multiplicacion

    assert suma != resta
    assert suma != multiplicacion
    assert resta != multiplicacion


def test_diferenciacion_estructuras_control():
    """Comprueba que estructuras If, For y While produzcan secuencias diferentes."""
    con_if = _serializar_codigo("def f(x):\n    if x:\n        pass\n")
    con_for = _serializar_codigo("def f(x):\n    for item in x:\n        pass\n")
    con_while = _serializar_codigo("def f(x):\n    while x:\n        pass\n")

    assert "If" in con_if and "For" not in con_if and "While" not in con_if
    assert "For" in con_for and "If" not in con_for and "While" not in con_for
    assert "While" in con_while and "If" not in con_while and "For" not in con_while

    assert con_if != con_for
    assert con_if != con_while
    assert con_for != con_while


def test_serializacion_es_determinista():
    """Comprueba que serializar repetidas veces el mismo AST devuelva la misma secuencia."""
    codigo = (
        "def procesar(datos):\n"
        "    total = 0\n"
        "    for x in datos:\n"
        "        total += x\n"
        "    return total\n"
    )
    nodo_normalizado = normalizar_ast(_obtener_funcion(codigo))

    referencia = serializar_ast(nodo_normalizado)
    for _ in range(10):
        assert serializar_ast(nodo_normalizado) == referencia


def test_conservacion_orden_y_repeticiones_tokens():
    """Comprueba que las repeticiones y el orden de los tokens no se pierdan."""
    codigo = "def f(x):\n    return x + x + x\n"
    tokens = _serializar_codigo(codigo)

    # Name:VAR1 debe aparecer exactamente 3 veces en la secuencia
    apariciones = [i for i, t in enumerate(tokens) if t == "Name:VAR1"]
    assert len(apariciones) == 3
    # El orden debe ser estrictamente creciente
    assert apariciones == sorted(apariciones)


def test_funciones_equivalentes_generan_secuencias_identicas():
    """Comprueba que funciones equivalentes con variables renombradas den secuencias idénticas."""
    primera = (
        "def sumar_elementos(numeros):\n"
        "    total = 0\n"
        "    for numero in numeros:\n"
        "        total += numero\n"
        "    return total\n"
    )
    segunda = (
        "def acumular_valores(valores):\n"
        "    resultado = 0\n"
        "    for valor in valores:\n"
        "        resultado += valor\n"
        "    return resultado\n"
    )
    assert _serializar_codigo(primera) == _serializar_codigo(segunda)


def test_funciones_estructuralmente_distintas_generan_secuencias_diferentes():
    """Comprueba que funciones distintas sintácticamente produzcan secuencias distintas."""
    paridad = "def es_par(n):\n    return n % 2 == 0\n"
    suma = "def sumar(a, b):\n    return a + b\n"

    assert _serializar_codigo(paridad) != _serializar_codigo(suma)


def test_arbol_recibido_no_se_modifica():
    """Comprueba que serializar no altere ningún nodo ni atributo del AST recibido."""
    codigo = "def ejemplo(a, b=10):\n    return a * b + 5\n"
    nodo_normalizado = normalizar_ast(_obtener_funcion(codigo))
    antes = ast.dump(nodo_normalizado, include_attributes=True)

    serializar_ast(nodo_normalizado)

    despues = ast.dump(nodo_normalizado, include_attributes=True)
    assert antes == despues


def test_integracion_completa_extractor_normalizador_serializador(tmp_path):
    """Comprueba la integración de todo el pipeline desde archivos en disco."""
    archivo = tmp_path / "modulo.py"
    archivo.write_text(
        "def calcular_area(base, altura):\n"
        "    return (base * altura) / 2\n"
        "\n"
        "def superficie_triangulo(b, h):\n"
        "    return (b * h) / 2\n",
        encoding="utf-8",
    )

    funciones = extraer_funciones_directorio(tmp_path)
    assert len(funciones) == 2

    tok_f1 = serializar_ast(normalizar_ast(funciones[0].nodo_ast))
    tok_f2 = serializar_ast(normalizar_ast(funciones[1].nodo_ast))

    assert tok_f1 == tok_f2
    assert "FunctionDef" in tok_f1
    assert "Div" in tok_f1
    assert "Mult" in tok_f1
    assert "Constant:LIT" in tok_f1


def test_rechaza_entrada_invalida():
    """Lanza TypeError si no se le pasa una instancia de ast.AST."""
    with pytest.raises(TypeError, match="ast.AST"):
        serializar_ast("no_es_un_ast")

    with pytest.raises(TypeError, match="ast.AST"):
        serializar_ast(None)


def test_funciones_asincronas_preservan_tipo():
    """Comprueba que async def comience con el token AsyncFunctionDef."""
    codigo = "async def consultar(dato):\n    return await fetch(dato)\n"
    tokens = _serializar_codigo(codigo)

    assert tokens[0] == "AsyncFunctionDef"
    assert "Await" in tokens


def test_ejemplos_reales_del_proyecto():
    """Verifica las funciones de ejemplo provistas en el proyecto."""
    directorio = Path(__file__).resolve().parent.parent / "ejemplos"
    funciones = {f.nombre: f for f in extraer_funciones_directorio(directorio)}

    tok_sumar = serializar_ast(normalizar_ast(funciones["sumar_elementos"].nodo_ast))
    tok_acumular = serializar_ast(normalizar_ast(funciones["acumular_valores"].nodo_ast))
    tok_par = serializar_ast(normalizar_ast(funciones["es_par"].nodo_ast))
    tok_factorial = serializar_ast(normalizar_ast(funciones["calcular_factorial"].nodo_ast))

    # Equivalentes entre sí
    assert tok_sumar == tok_acumular

    # Distintas entre sí
    assert tok_sumar != tok_par
    assert tok_sumar != tok_factorial
    assert tok_par != tok_factorial
