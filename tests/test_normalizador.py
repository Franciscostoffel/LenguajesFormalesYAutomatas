"""Pruebas de equivalencia estructural y conservación del AST original."""

import ast
from pathlib import Path

import pytest

from motor_ast.extractor import extraer_funciones_directorio
from motor_ast.normalizador import normalizar_ast


def _funcion(codigo):
    return ast.parse(codigo).body[0]


def _estructura_normalizada(codigo):
    return ast.dump(normalizar_ast(_funcion(codigo)), include_attributes=False)


def test_variables_renombradas_son_equivalentes():
    primera = "def sumar(a, b):\n    resultado = a + b\n    return resultado\n"
    segunda = "def sumar(x, y):\n    total = x + y\n    return total\n"

    assert _estructura_normalizada(primera) == _estructura_normalizada(segunda)


def test_nombre_de_funcion_no_influye():
    assert _estructura_normalizada("def suma(a):\n    return a\n") == _estructura_normalizada(
        "def operacion(a):\n    return a\n"
    )


@pytest.mark.parametrize("literal", ["10", "25", "3.5", "2j", "'hola'", '"otro texto"', "u'texto'"])
def test_numeros_y_cadenas_se_reemplazan_por_lit(literal):
    normalizado = normalizar_ast(_funcion(f"def f():\n    return {literal}\n"))

    assert isinstance(normalizado.body[0].value, ast.Constant)
    assert normalizado.body[0].value.value == "LIT"
    assert _estructura_normalizada(f"def f():\n    return {literal}\n") == _estructura_normalizada(
        "def g():\n    return 99\n"
    )


def test_misma_variable_conserva_correspondencia_y_distintas_no_se_confunden():
    normalizado = normalizar_ast(_funcion(
        "def calcular(precio, cantidad):\n"
        "    subtotal = precio * cantidad\n"
        "    return subtotal + precio\n"
    ))

    assert normalizado.name == "FUNC"
    assert [arg.arg for arg in normalizado.args.args] == ["VAR1", "VAR2"]
    asignacion, retorno = normalizado.body
    assert asignacion.targets[0].id == "VAR3"
    assert asignacion.value.left.id == "VAR1"
    assert asignacion.value.right.id == "VAR2"
    assert retorno.value.left.id == "VAR3"
    assert retorno.value.right.id == "VAR1"


def test_contador_se_reinicia_y_resultado_es_determinista():
    original = _funcion("def f(a):\n    b = a\n    return b\n")
    primera = normalizar_ast(original)
    normalizar_ast(_funcion("def otra(x, y, z):\n    return x + y + z\n"))
    segunda = normalizar_ast(original)

    assert primera.args.args[0].arg == segunda.args.args[0].arg == "VAR1"
    assert ast.dump(primera) == ast.dump(segunda)
    assert primera is not segunda


def test_add_y_mult_se_conservan_diferentes():
    suma = normalizar_ast(_funcion("def f(a, b):\n    return a + b\n"))
    producto = normalizar_ast(_funcion("def g(x, y):\n    return x * y\n"))

    assert isinstance(suma.body[0].value.op, ast.Add)
    assert isinstance(producto.body[0].value.op, ast.Mult)
    assert ast.dump(suma) != ast.dump(producto)


def test_preserva_estructura_contextos_y_ubicaciones():
    original = _funcion(
        "def f(valores):\n"
        "    total = 0\n"
        "    for valor in valores:\n"
        "        if valor > 2:\n"
        "            total += valor\n"
        "    while total < 10:\n"
        "        total += 1\n"
        "    return abs(total)\n"
    )
    normalizado = normalizar_ast(original)

    assert [type(nodo) for nodo in ast.walk(normalizado)] == [type(nodo) for nodo in ast.walk(original)]
    for antes, despues in zip(ast.walk(original), ast.walk(normalizado)):
        for atributo in ("lineno", "col_offset", "end_lineno", "end_col_offset"):
            assert getattr(antes, atributo, None) == getattr(despues, atributo, None)


def test_original_y_copia_son_independientes():
    original = _funcion("def original(a=10):\n    return a + 20\n")
    antes = ast.dump(original, include_attributes=True)

    normalizado = normalizar_ast(original)

    assert ast.dump(original, include_attributes=True) == antes
    assert original.name == "original"
    assert original.args.defaults[0].value == 10
    assert normalizado is not original
    assert normalizado.args is not original.args
    normalizado.args.args[0].arg = "CAMBIADO"
    assert original.args.args[0].arg == "a"


def test_integracion_con_extractor(tmp_path):
    archivo = tmp_path / "funciones.py"
    archivo.write_text(
        "def primera(a):\n    return a * 10\n\ndef segunda(x):\n    return x * 25\n",
        encoding="utf-8",
    )
    primera, segunda = extraer_funciones_directorio(tmp_path)

    assert ast.dump(normalizar_ast(primera.nodo_ast)) == ast.dump(normalizar_ast(segunda.nodo_ast))
    assert (primera.nombre, segunda.nombre) == ("primera", "segunda")
    assert primera.nodo_ast.name == "primera"
    assert primera.nodo_ast.body[0].value.right.value == 10


def test_ejemplos_existentes_son_equivalentes():
    directorio = Path(__file__).resolve().parent.parent / "ejemplos"
    funciones = {f.nombre: f for f in extraer_funciones_directorio(directorio)}

    assert ast.dump(normalizar_ast(funciones["sumar_elementos"].nodo_ast)) == ast.dump(
        normalizar_ast(funciones["acumular_valores"].nodo_ast)
    )


def test_atributos_y_etiquetas_keyword_se_conservan():
    normalizado = normalizar_ast(_funcion("def f(obj, dato):\n    return obj.metodo(dato, limite=3)\n"))
    llamada = normalizado.body[0].value

    assert llamada.func.value.id == "VAR1"
    assert llamada.func.attr == "metodo"
    assert llamada.args[0].id == "VAR2"
    assert llamada.keywords[0].arg == "limite"
    assert llamada.keywords[0].value.value == "LIT"


def test_nombres_externos_y_builtin_siguen_la_misma_regla():
    primera = "def f(datos):\n    return len(datos) + CONSTANTE\n"
    segunda = "def g(items):\n    return medir(items) + LIMITE\n"

    assert _estructura_normalizada(primera) == _estructura_normalizada(segunda)


def test_funciones_anidadas_comparten_mapa_y_renombran_referencias():
    primera = "def f(a):\n    def interna(b):\n        return a + b\n    return interna(a)\n"
    segunda = "def g(x):\n    def auxiliar(y):\n        return x + y\n    return auxiliar(x)\n"
    normalizado = normalizar_ast(_funcion(primera))
    interna = normalizado.body[0]

    assert _estructura_normalizada(primera) == _estructura_normalizada(segunda)
    assert interna.name == normalizado.body[1].value.func.id == "VAR2"
    assert interna.args.args[0].arg == "VAR3"
    assert interna.body[0].value.left.id == "VAR1"


def test_sombreado_comparte_nombre_segun_politica_simplificada():
    normalizado = normalizar_ast(_funcion(
        "def f(a):\n    def interna(a):\n        return a\n    return a\n"
    ))

    assert normalizado.args.args[0].arg == normalizado.body[0].args.args[0].arg == "VAR1"


def test_parametros_se_registran_antes_de_anotaciones_y_defaults():
    normalizado = normalizar_ast(_funcion(
        "def f(a: int, /, b=10, *resto, c=20, **opciones):\n    return a, b, resto, c, opciones\n"
    ))
    argumentos = normalizado.args

    assert [argumentos.posonlyargs[0].arg, argumentos.args[0].arg, argumentos.vararg.arg,
            argumentos.kwonlyargs[0].arg, argumentos.kwarg.arg] == [f"VAR{i}" for i in range(1, 6)]
    assert argumentos.posonlyargs[0].annotation.id == "VAR6"
    assert argumentos.defaults[0].value == argumentos.kw_defaults[0].value == "LIT"


def test_async_preserva_su_tipo_y_await():
    normalizado = normalizar_ast(_funcion("async def tarea(dato):\n    return await consultar(dato)\n"))

    assert isinstance(normalizado, ast.AsyncFunctionDef)
    assert normalizado.name == "FUNC"
    assert isinstance(normalizado.body[0].value, ast.Await)


def test_bool_none_bytes_y_ellipsis_se_conservan():
    normalizado = normalizar_ast(_funcion("def f():\n    return True, False, None, b'abc', ...\n"))

    assert [nodo.value for nodo in normalizado.body[0].value.elts] == [True, False, None, b"abc", Ellipsis]


def test_fstring_conserva_estructura_y_admite_visualizacion():
    normalizado = normalizar_ast(_funcion("def f(nombre):\n    return f'hola {nombre}'\n"))

    assert isinstance(normalizado.body[0].value, ast.JoinedStr)
    assert normalizado.body[0].value.values[0].value == "LIT"
    ast.parse(ast.unparse(normalizado))


def test_docstring_se_normaliza_sin_eliminar_su_nodo():
    primera = "def f():\n    'primera descripcion'\n    return 1\n"
    segunda = "def g():\n    'otra descripcion'\n    return 20\n"

    assert _estructura_normalizada(primera) == _estructura_normalizada(segunda)
    assert isinstance(normalizar_ast(_funcion(primera)).body[0], ast.Expr)


def test_rechaza_entrada_que_no_es_una_funcion():
    with pytest.raises(TypeError, match="FunctionDef o AsyncFunctionDef"):
        normalizar_ast(ast.parse("x = 1"))
