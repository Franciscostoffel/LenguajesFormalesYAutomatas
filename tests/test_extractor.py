"""Pruebas de extracción con código y archivos temporales reales."""

import ast
from pathlib import Path

import pytest

from motor_ast.extractor import (
    encontrar_archivos_python,
    extraer_funciones,
    extraer_funciones_directorio,
    parsear_archivo,
)


def test_extraer_funcion_simple_con_metadatos(tmp_path):
    archivo = tmp_path / "suma.py"
    archivo.write_text("\ndef sumar(a, b):\n    return a + b\n", encoding="utf-8")

    arbol = parsear_archivo(archivo)
    funciones = extraer_funciones(arbol, archivo)

    assert isinstance(arbol, ast.Module)
    assert len(funciones) == 1
    funcion = funciones[0]
    assert funcion.nombre == "sumar"
    assert funcion.archivo == archivo
    assert funcion.linea == 2
    assert isinstance(funcion.nodo_ast, ast.FunctionDef)
    assert funcion.nodo_ast is arbol.body[0]
    assert isinstance(funcion.nodo_ast.body[0].value, ast.BinOp)


def test_extraer_varias_funciones_en_orden_de_linea():
    arbol = ast.parse("def primera():\n    pass\n\ndef segunda():\n    pass\n")

    funciones = extraer_funciones(arbol, Path("funciones.py"))

    assert [(f.nombre, f.linea) for f in funciones] == [("primera", 1), ("segunda", 4)]


def test_recorrido_recursivo_ordenado_ignora_otras_extensiones(tmp_path):
    subdirectorio = tmp_path / "subcarpeta"
    subdirectorio.mkdir()
    # Crear primero z.py permite comprobar que no se usa el orden de creación.
    (tmp_path / "z.py").write_text("def ultima():\n    pass\n", encoding="utf-8")
    (subdirectorio / "b.py").write_text("def interna():\n    pass\n", encoding="utf-8")
    (tmp_path / "a.py").write_text("def primera():\n    pass\n", encoding="utf-8")
    (tmp_path / "notas.txt").write_text("esto no es Python válido", encoding="utf-8")
    (tmp_path / "carpeta.py").mkdir()

    archivos = encontrar_archivos_python(str(tmp_path))
    funciones = extraer_funciones_directorio(tmp_path)

    assert archivos == [tmp_path / "a.py", subdirectorio / "b.py", tmp_path / "z.py"]
    assert [f.nombre for f in funciones] == ["primera", "interna", "ultima"]
    assert [f.archivo for f in funciones] == archivos
    assert encontrar_archivos_python(tmp_path) == archivos


def test_extraer_funciones_anidadas_metodos_y_async():
    arbol = ast.parse(
        "def exterior():\n"
        "    def interior():\n"
        "        pass\n"
        "    return interior\n"
        "class Servicio:\n"
        "    def metodo(self):\n"
        "        pass\n"
        "    async def consultar(self):\n"
        "        pass\n"
        "async def tarea():\n"
        "    pass\n"
    )

    funciones = extraer_funciones(arbol, "anidadas.py")

    assert [(f.nombre, f.linea) for f in funciones] == [
        ("exterior", 1), ("interior", 2), ("metodo", 6), ("consultar", 8), ("tarea", 10),
    ]
    assert isinstance(funciones[3].nodo_ast, ast.AsyncFunctionDef)
    assert isinstance(funciones[4].nodo_ast, ast.AsyncFunctionDef)
    assert all(isinstance(f.nodo_ast, (ast.FunctionDef, ast.AsyncFunctionDef)) for f in funciones)


def test_extraccion_no_modifica_ast():
    arbol = ast.parse("def original(valor=42):\n    return valor + 1\n")
    antes = ast.dump(arbol, include_attributes=True)

    extraer_funciones(arbol, "original.py")

    assert ast.dump(arbol, include_attributes=True) == antes


def test_no_ejecuta_codigo_ni_modifica_archivos(tmp_path):
    archivo = tmp_path / "peligroso.py"
    codigo = b"raise RuntimeError('No ejecutar')\n\ndef funcion():\n    return 1\n"
    archivo.write_bytes(codigo)

    funciones = extraer_funciones_directorio(tmp_path)

    assert [f.nombre for f in funciones] == ["funcion"]
    assert archivo.read_bytes() == codigo


def test_archivo_con_error_de_sintaxis_se_omite_y_continua(tmp_path, caplog):
    (tmp_path / "a.py").write_text("def primera():\n    pass\n", encoding="utf-8")
    archivo = tmp_path / "b_invalido.py"
    archivo.write_text("def rota(:\n    pass\n", encoding="utf-8")
    (tmp_path / "c.py").write_text("def ultima():\n    pass\n", encoding="utf-8")

    funciones = extraer_funciones_directorio(tmp_path)

    assert [f.nombre for f in funciones] == ["primera", "ultima"]
    assert str(archivo) in caplog.text
    assert "Se omite el archivo" in caplog.text


def test_parsear_archivo_propaga_error_de_sintaxis(tmp_path):
    archivo = tmp_path / "invalido.py"
    archivo.write_text("def rota(:\n    pass\n", encoding="utf-8")

    with pytest.raises(SyntaxError) as error:
        parsear_archivo(archivo)

    assert error.value.filename == str(archivo)
    assert error.value.lineno == 1


def test_directorio_inexistente(tmp_path):
    with pytest.raises(FileNotFoundError, match="El directorio no existe"):
        extraer_funciones_directorio(tmp_path / "inexistente")


def test_archivo_no_es_directorio(tmp_path):
    archivo = tmp_path / "archivo.py"
    archivo.touch()

    with pytest.raises(NotADirectoryError, match="La ruta no es un directorio"):
        encontrar_archivos_python(archivo)


def test_archivo_inexistente_al_parsear(tmp_path):
    with pytest.raises(FileNotFoundError):
        parsear_archivo(tmp_path / "ausente.py")


def test_error_de_lectura_al_parsear_directorio(tmp_path):
    with pytest.raises(OSError):
        parsear_archivo(tmp_path)


def test_archivo_con_codificacion_declarada(tmp_path):
    archivo = tmp_path / "latin1.py"
    archivo.write_bytes("# coding: latin-1\ndef saludar():\n    return 'hola, señor'\n".encode("latin-1"))

    funciones = extraer_funciones_directorio(tmp_path)

    assert funciones[0].nodo_ast.body[0].value.value == "hola, señor"


def test_error_de_codificacion_se_omite_y_continua(tmp_path, caplog):
    archivo = tmp_path / "codificacion_invalida.py"
    archivo.write_bytes(b"# coding: utf-8\n# \xff\n")
    (tmp_path / "valido.py").write_text("def valida():\n    pass\n", encoding="utf-8")

    funciones = extraer_funciones_directorio(tmp_path)

    assert [f.nombre for f in funciones] == ["valida"]
    assert str(archivo) in caplog.text

    with pytest.raises(UnicodeError):
        parsear_archivo(archivo)


def test_directorio_con_solo_archivos_invalidos(tmp_path, caplog):
    (tmp_path / "invalido.py").write_text("def rota(:\n", encoding="utf-8")

    assert extraer_funciones_directorio(tmp_path) == []
    assert "Se omite el archivo" in caplog.text


def test_directorio_vacio(tmp_path):
    assert encontrar_archivos_python(tmp_path) == []
    assert extraer_funciones_directorio(tmp_path) == []


def test_archivo_sin_funciones(tmp_path):
    archivo = tmp_path / "constantes.py"
    archivo.write_text("VALOR = 42\n", encoding="utf-8")

    assert extraer_funciones_directorio(tmp_path) == []
