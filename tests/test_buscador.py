"""Pruebas del motor de búsqueda Top-K y de la interfaz CLI (buscar_similares.py)."""

from pathlib import Path

import pytest

from buscar_similares import crear_parser, formatear_reporte, main
from motor_ast.buscador import (
    ReporteBusqueda,
    ResultadoSimilitud,
    buscar_similares,
    ejecutar_busqueda,
    identificar_funcion_objetivo,
)
from motor_ast.extractor import extraer_funciones_directorio


# ==============================================================================
# A. Pruebas del Buscador y Localización de la Función Objetivo
# ==============================================================================


def test_modulos_importables():
    """Comprueba que todos los módulos del paquete sean importables."""
    from importlib import import_module

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


def test_identificar_funcion_objetivo_correcta():
    """Localiza una función existente en un archivo de ejemplos."""
    directorio = Path(__file__).resolve().parent.parent / "ejemplos"
    funciones = extraer_funciones_directorio(directorio)

    objetivo = identificar_funcion_objetivo(
        funciones,
        referencia="funciones_similares.py:sumar_elementos",
        directorio=directorio,
    )

    assert objetivo.nombre == "sumar_elementos"
    assert objetivo.archivo.name == "funciones_similares.py"


def test_identificar_funcion_con_ruta_completa_o_relativa():
    """Localiza la función cuando se especifica la ruta relativa completa."""
    directorio = Path(__file__).resolve().parent.parent / "ejemplos"
    funciones = extraer_funciones_directorio(directorio)

    objetivo = identificar_funcion_objetivo(
        funciones,
        referencia="ejemplos/funciones_similares.py:sumar_elementos",
        directorio=directorio.parent,
    )

    assert objetivo.nombre == "sumar_elementos"


def test_identificar_funcion_inexistente():
    """Lanza ValueError si la función no existe en el archivo."""
    directorio = Path(__file__).resolve().parent.parent / "ejemplos"
    funciones = extraer_funciones_directorio(directorio)

    with pytest.raises(ValueError, match="No se encontró la función"):
        identificar_funcion_objetivo(
            funciones,
            referencia="funciones_similares.py:no_existe",
            directorio=directorio,
        )


def test_identificar_archivo_inexistente():
    """Lanza FileNotFoundError si el archivo no está en el repositorio."""
    directorio = Path(__file__).resolve().parent.parent / "ejemplos"
    funciones = extraer_funciones_directorio(directorio)

    with pytest.raises(FileNotFoundError, match="No se encontró el archivo"):
        identificar_funcion_objetivo(
            funciones,
            referencia="archivo_fantasma.py:sumar",
            directorio=directorio,
        )


def test_identificar_formato_invalido():
    """Lanza ValueError si la referencia no incluye dos puntos ':'."""
    directorio = Path(__file__).resolve().parent.parent / "ejemplos"
    funciones = extraer_funciones_directorio(directorio)

    with pytest.raises(ValueError, match="Formato de función inválido"):
        identificar_funcion_objetivo(funciones, referencia="solo_nombre", directorio=directorio)

    with pytest.raises(ValueError, match="Formato de función inválido"):
        identificar_funcion_objetivo(funciones, referencia=":sin_archivo", directorio=directorio)


def test_referencia_ambigua_mismo_nombre_en_mismo_archivo(tmp_path):
    """Lanza ValueError si hay dos definiciones del mismo nombre en el mismo archivo."""
    archivo = tmp_path / "ambiguo.py"
    archivo.write_text(
        "def duplicada():\n    pass\n\ndef duplicada():\n    return 1\n",
        encoding="utf-8",
    )
    funciones = extraer_funciones_directorio(tmp_path)

    with pytest.raises(ValueError, match="Referencia ambigua"):
        identificar_funcion_objetivo(
            funciones,
            referencia="ambiguo.py:duplicada",
            directorio=tmp_path,
        )


def test_mismo_nombre_en_distintos_archivos_se_diferencia(tmp_path):
    """Funciones con igual nombre en archivos distintos se resuelven sin conflicto."""
    dir_a = tmp_path / "modulo_a"
    dir_b = tmp_path / "modulo_b"
    dir_a.mkdir()
    dir_b.mkdir()

    (dir_a / "servicio.py").write_text("def ejecutar():\n    return 10\n", encoding="utf-8")
    (dir_b / "servicio.py").write_text("def ejecutar():\n    return 20\n", encoding="utf-8")

    funciones = extraer_funciones_directorio(tmp_path)

    obj_a = identificar_funcion_objetivo(
        funciones,
        referencia="modulo_a/servicio.py:ejecutar",
        directorio=tmp_path,
    )
    obj_b = identificar_funcion_objetivo(
        funciones,
        referencia="modulo_b/servicio.py:ejecutar",
        directorio=tmp_path,
    )

    assert obj_a.archivo.parent.name == "modulo_a"
    assert obj_b.archivo.parent.name == "modulo_b"


# ==============================================================================
# B. Pruebas del Algoritmo de Búsqueda y Ranking Top-K
# ==============================================================================


def test_buscar_excluye_funcion_objetivo():
    """La función objetivo nunca debe aparecer en su propio ranking de resultados."""
    directorio = Path(__file__).resolve().parent.parent / "ejemplos"
    resultados = buscar_similares(
        directorio=directorio,
        funcion="funciones_similares.py:sumar_elementos",
        top_k=5,
    )

    # Debe encontrar las otras 3 funciones, pero nunca 'sumar_elementos' en funciones_similares.py
    for r in resultados:
        assert not (r.nombre == "sumar_elementos" and r.archivo.name == "funciones_similares.py")


def test_buscar_orden_descendente_por_score():
    """Los resultados deben estar ordenados estrictamente de mayor a menor score."""
    directorio = Path(__file__).resolve().parent.parent / "ejemplos"
    resultados = buscar_similares(
        directorio=directorio,
        funcion="funciones_similares.py:sumar_elementos",
        top_k=5,
    )

    scores = [r.score for r in resultados]
    assert scores == sorted(scores, reverse=True)


def test_buscar_respeta_top_k():
    """Si se solicita top_k=1, debe devolver a lo sumo 1 resultado."""
    directorio = Path(__file__).resolve().parent.parent / "ejemplos"
    resultados = buscar_similares(
        directorio=directorio,
        funcion="funciones_similares.py:sumar_elementos",
        top_k=1,
    )

    assert len(resultados) == 1
    assert resultados[0].nombre == "acumular_valores"
    assert resultados[0].score == 1.0


def test_buscar_menos_candidatas_que_k():
    """Si hay menos funciones candidatas que K, devuelve solo las existentes."""
    directorio = Path(__file__).resolve().parent.parent / "ejemplos"
    resultados = buscar_similares(
        directorio=directorio,
        funcion="funciones_similares.py:sumar_elementos",
        top_k=100,
    )

    # En ejemplos hay 4 funciones en total: 1 objetivo + 3 candidatas
    assert len(resultados) == 3


def test_clasificacion_segun_umbral():
    """Verifica que el flag es_duplicado respete el umbral configurado."""
    directorio = Path(__file__).resolve().parent.parent / "ejemplos"

    # Con umbral 0.75, solo acumular_valores (score 1.0) supera el umbral
    res_75 = buscar_similares(
        directorio=directorio,
        funcion="funciones_similares.py:sumar_elementos",
        umbral=0.75,
    )
    dups_75 = [r for r in res_75 if r.es_duplicado]
    assert len(dups_75) == 1
    assert dups_75[0].nombre == "acumular_valores"

    # Con umbral 0.10, acumular_valores (1.0) y factorial (~0.20) lo superan
    res_10 = buscar_similares(
        directorio=directorio,
        funcion="funciones_similares.py:sumar_elementos",
        umbral=0.10,
    )
    dups_10 = [r for r in res_10 if r.es_duplicado]
    assert len(dups_10) == 2


def test_desempate_determinista_ante_scores_iguales(tmp_path):
    """Comprueba que funciones con idéntico score desempaten deterministamente por ruta y línea."""
    archivo_a = tmp_path / "a.py"
    archivo_b = tmp_path / "b.py"

    codigo = "def operacion(x):\n    return x + 1\n"
    archivo_a.write_text(codigo, encoding="utf-8")
    archivo_b.write_text(codigo, encoding="utf-8")

    # Archivo objetivo
    obj_file = tmp_path / "target.py"
    obj_file.write_text("def objetivo(n):\n    return n + 1\n", encoding="utf-8")

    resultados = buscar_similares(
        directorio=tmp_path,
        funcion="target.py:objetivo",
        top_k=5,
    )

    assert len(resultados) == 2
    assert resultados[0].score == resultados[1].score == 1.0
    # a.py debe preceder a b.py por orden alfabético de ruta
    assert resultados[0].archivo.name == "a.py"
    assert resultados[1].archivo.name == "b.py"


def test_repositorio_solo_con_funcion_objetivo(tmp_path):
    """Si el repositorio tiene una sola función, devuelve lista vacía sin error."""
    archivo = tmp_path / "unica.py"
    archivo.write_text("def solitaria():\n    pass\n", encoding="utf-8")

    reporte = ejecutar_busqueda(
        directorio=tmp_path,
        funcion="unica.py:solitaria",
        top_k=5,
    )

    assert reporte.total_encontradas == 1
    assert reporte.total_comparadas == 0
    assert reporte.resultados == []


def test_repositorio_sin_funciones(tmp_path):
    """Lanza ValueError si el directorio no contiene funciones Python."""
    archivo = tmp_path / "constantes.py"
    archivo.write_text("X = 1\n", encoding="utf-8")

    with pytest.raises(ValueError, match="No se encontraron funciones"):
        buscar_similares(directorio=tmp_path, funcion="constantes.py:algo")


@pytest.mark.parametrize("top_k_invalido", [0, -1, -10, "5", 2.5])
def test_validaciones_top_k(top_k_invalido):
    """Comprueba que top_k inválido lance ValueError."""
    directorio = Path(__file__).resolve().parent.parent / "ejemplos"
    with pytest.raises(ValueError, match="top_k debe ser un entero positivo"):
        buscar_similares(
            directorio=directorio,
            funcion="funciones_similares.py:sumar_elementos",
            top_k=top_k_invalido,
        )


# ==============================================================================
# C. Pruebas de la Interfaz CLI (buscar_similares.py)
# ==============================================================================


def test_cli_parser_argumentos_correctos():
    """Verifica que el parser lea correctamente los argumentos y use los defaults."""
    parser = crear_parser()
    args = parser.parse_args(["--dir", "./ejemplos", "--funcion", "f.py:foo"])

    assert args.directorio == "./ejemplos"
    assert args.funcion == "f.py:foo"
    assert args.top_k == 5
    assert args.umbral == 0.75
    assert args.n == 3


def test_cli_parser_argumentos_personalizados():
    """Verifica que los argumentos personalizados sobrescriban los defaults."""
    parser = crear_parser()
    args = parser.parse_args([
        "--dir", "./repo",
        "--funcion", "f.py:bar",
        "--top", "10",
        "--umbral", "0.85",
        "--n", "4",
    ])

    assert args.top_k == 10
    assert args.umbral == 0.85
    assert args.n == 4


def test_cli_ejecucion_exitosa(capsys):
    """Ejecuta main() de la CLI con argumentos válidos y verifica la salida en consola."""
    directorio = str(Path(__file__).resolve().parent.parent / "ejemplos")
    codigo_retorno = main([
        "--dir", directorio,
        "--funcion", "funciones_similares.py:sumar_elementos",
        "--top", "3",
    ])

    captura = capsys.readouterr()

    assert codigo_retorno == 0
    assert "MOTOR DE BÚSQUEDA DE FUNCIONES VIA AST" in captura.out
    assert "sumar_elementos" in captura.out
    assert "acumular_valores" in captura.out
    assert "Candidata a duplicado: SÍ" in captura.out
    assert "Funciones encontradas: 4" in captura.out
    assert "Funciones comparadas: 3" in captura.out


def test_cli_error_directorio_inexistente(capsys):
    """Comprueba que un directorio inexistente imprima el error en stderr y devuelva 1."""
    codigo_retorno = main([
        "--dir", "./directorio_que_no_existe_xyz",
        "--funcion", "archivo.py:func",
    ])

    captura = capsys.readouterr()

    assert codigo_retorno == 1
    assert "Error:" in captura.err
    assert "El directorio no existe" in captura.err


def test_cli_error_funcion_inexistente(capsys):
    """Comprueba que una función inexistente imprima el error en stderr y devuelva 1."""
    directorio = str(Path(__file__).resolve().parent.parent / "ejemplos")
    codigo_retorno = main([
        "--dir", directorio,
        "--funcion", "funciones_similares.py:no_existe",
    ])

    captura = capsys.readouterr()

    assert codigo_retorno == 1
    assert "Error: No se encontró la función" in captura.err


def test_cli_salida_sin_candidatos(tmp_path, capsys):
    """Comprueba el formato de salida cuando solo existe la función objetivo."""
    archivo = tmp_path / "unica.py"
    archivo.write_text("def sola(): pass\n", encoding="utf-8")

    codigo_retorno = main([
        "--dir", str(tmp_path),
        "--funcion", "unica.py:sola",
    ])

    captura = capsys.readouterr()

    assert codigo_retorno == 0
    assert "No se encontraron otras funciones para comparar" in captura.out
    assert "Resultados mostrados: 0" in captura.out
