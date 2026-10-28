"""Pruebas de similitud estructural mediante Jaccard sobre n-gramas de tokens."""

import ast
from pathlib import Path

import pytest

from motor_ast.extractor import extraer_funciones_directorio
from motor_ast.normalizador import normalizar_ast
from motor_ast.serializador import serializar_ast
from motor_ast.similitud import es_candidato_duplicado, generar_ngramas, similitud_jaccard


def _tokens_de_codigo(codigo: str) -> list[str]:
    """Helper que ejecuta el pipeline completo sobre un fragmento de función."""
    nodo = ast.parse(codigo).body[0]
    return serializar_ast(normalizar_ast(nodo))


# ==============================================================================
# A. Pruebas de generación de n-gramas
# ==============================================================================


def test_generar_unigramas():
    """Verifica que n=1 genere tuplas de 1 elemento."""
    tokens = ["FunctionDef", "arguments", "Return"]
    ngramas = generar_ngramas(tokens, n=1)

    assert ngramas == {("FunctionDef",), ("arguments",), ("Return",)}


def test_generar_bigramas():
    """Verifica que n=2 genere pares consecutivos de tokens."""
    tokens = ["FunctionDef", "arguments", "Return"]
    ngramas = generar_ngramas(tokens, n=2)

    assert ngramas == {
        ("FunctionDef", "arguments"),
        ("arguments", "Return"),
    }


def test_generar_trigramas():
    """Verifica que n=3 genere ternas consecutivas de tokens."""
    tokens = ["Return", "BinOp", "Name:VAR1", "Add", "Name:VAR2"]
    ngramas = generar_ngramas(tokens, n=3)

    assert ngramas == {
        ("Return", "BinOp", "Name:VAR1"),
        ("BinOp", "Name:VAR1", "Add"),
        ("Name:VAR1", "Add", "Name:VAR2"),
    }


def test_conservacion_orden_interno_de_tokens_en_ngrama():
    """Comprueba que el orden relativo de los tokens dentro de cada tupla se respete."""
    tokens = ["A", "B", "C"]
    ngramas = generar_ngramas(tokens, n=3)

    assert ("A", "B", "C") in ngramas
    assert ("C", "B", "A") not in ngramas


def test_eliminacion_ngramas_duplicados_al_convertir_en_conjunto():
    """Comprueba que subsecuencias repetidas se unifiquen en el conjunto devuelto."""
    tokens = ["Add", "Name:VAR1", "Add", "Name:VAR1"]
    bigramas = generar_ngramas(tokens, n=2)

    # Las subsecuencias son ("Add", "Name:VAR1"), ("Name:VAR1", "Add"), ("Add", "Name:VAR1")
    # Al ser un set, solo debe haber 2 bigramas únicos
    assert len(bigramas) == 2
    assert ("Add", "Name:VAR1") in bigramas
    assert ("Name:VAR1", "Add") in bigramas


def test_secuencias_cortas_menores_a_n():
    """Comprueba que secuencias no vacías con len < n formen un único n-grama."""
    tokens = ["Return", "Constant:LIT"]
    ngramas = generar_ngramas(tokens, n=3)

    assert ngramas == {("Return", "Constant:LIT")}


def test_secuencia_vacia_produce_conjunto_vacio():
    """Comprueba que una lista vacía devuelva set()."""
    assert generar_ngramas([], n=3) == set()


@pytest.mark.parametrize("n_invalido", [0, -1, -5, "3", 2.5, None])
def test_rechazo_valores_invalidos_de_n(n_invalido):
    """Comprueba que valores inválidos de n lancen ValueError."""
    with pytest.raises(ValueError, match="entero positivo >= 1"):
        generar_ngramas(["A", "B", "C"], n=n_invalido)


# ==============================================================================
# B. Pruebas de la métrica de Jaccard
# ==============================================================================


def test_jaccard_secuencias_identicas_produce_uno():
    """Comprueba que dos secuencias idénticas obtengan puntuación 1.0."""
    tokens = ["FunctionDef", "arguments", "Return", "Constant:LIT"]
    assert similitud_jaccard(tokens, tokens, n=3) == 1.0


def test_jaccard_secuencias_disjuntas_produce_cero():
    """Comprueba que secuencias sin n-gramas compartidos obtengan 0.0."""
    tokens_a = ["A", "B", "C", "D"]
    tokens_b = ["W", "X", "Y", "Z"]

    assert similitud_jaccard(tokens_a, tokens_b, n=3) == 0.0


def test_jaccard_valor_intermedio():
    """Comprueba el cálculo exacto de Jaccard en un caso parcialmente similar.

    A = {('A', 'B'), ('B', 'C'), ('C', 'D')}  -> 3 elementos
    B = {('B', 'C'), ('C', 'D'), ('D', 'E')}  -> 3 elementos
    Intersección = {('B', 'C'), ('C', 'D')}   -> 2 elementos
    Unión = {('A', 'B'), ('B', 'C'), ('C', 'D'), ('D', 'E')} -> 4 elementos
    Jaccard = 2 / 4 = 0.50
    """
    tokens_a = ["A", "B", "C", "D"]
    tokens_b = ["B", "C", "D", "E"]

    assert similitud_jaccard(tokens_a, tokens_b, n=2) == 0.50


def test_jaccard_es_simetrica():
    """Comprueba que J(A, B) == J(B, A)."""
    tokens_a = ["FunctionDef", "arguments", "Return", "BinOp", "Add"]
    tokens_b = ["FunctionDef", "arguments", "Return", "Constant:LIT"]

    assert similitud_jaccard(tokens_a, tokens_b, n=3) == similitud_jaccard(tokens_b, tokens_a, n=3)


def test_jaccard_intervalo_acotado():
    """Comprueba que el score se encuentre siempre dentro de [0.0, 1.0]."""
    casos = [
        (["A", "B"], ["C", "D"]),
        (["A", "B", "C"], ["A", "B", "C"]),
        (["A", "B", "C"], ["A", "B", "D"]),
    ]
    for ta, tb in casos:
        score = similitud_jaccard(ta, tb, n=2)
        assert 0.0 <= score <= 1.0


def test_jaccard_casos_secuencias_vacias():
    """Verifica los casos límite con secuencias vacías."""
    # Ambas vacías: similitud 1.0 por convención
    assert similitud_jaccard([], [], n=3) == 1.0

    # Una vacía y otra no: similitud 0.0
    tokens = ["FunctionDef", "Return"]
    assert similitud_jaccard(tokens, [], n=3) == 0.0
    assert similitud_jaccard([], tokens, n=3) == 0.0


def test_jaccard_es_determinista():
    """Comprueba que evaluar repetidamente las mismas secuencias devuelva el mismo score."""
    tokens_a = ["FunctionDef", "arguments", "arg:VAR1", "Return", "BinOp", "Add"]
    tokens_b = ["FunctionDef", "arguments", "arg:VAR1", "Return", "BinOp", "Mult"]

    referencia = similitud_jaccard(tokens_a, tokens_b, n=3)
    for _ in range(10):
        assert similitud_jaccard(tokens_a, tokens_b, n=3) == referencia


def test_jaccard_no_modifica_secuencias_recibidas():
    """Comprueba que similitud_jaccard no altere las listas de entrada."""
    tokens_a = ["A", "B", "C"]
    tokens_b = ["B", "C", "D"]
    copia_a = list(tokens_a)
    copia_b = list(tokens_b)

    similitud_jaccard(tokens_a, tokens_b, n=2)

    assert tokens_a == copia_a
    assert tokens_b == copia_b


# ==============================================================================
# C. Casos positivos del Trabajo Práctico (Integración completa)
# ==============================================================================


def test_caso_positivo_variables_renombradas():
    """Caso positivo 1: funciones idénticas salvo renombrado de variables y parámetros.

    Debe alcanzar un score de 1.0 (100%) y ser clasificada como candidata a duplicado.
    """
    f1 = (
        "def sumar(a, b):\n"
        "    resultado = a + b\n"
        "    return resultado\n"
    )
    f2 = (
        "def calcular(x, y):\n"
        "    total = x + y\n"
        "    return total\n"
    )
    tokens_1 = _tokens_de_codigo(f1)
    tokens_2 = _tokens_de_codigo(f2)

    score = similitud_jaccard(tokens_1, tokens_2, n=3)

    assert score == 1.0
    assert es_candidato_duplicado(score, umbral=0.75) is True


def test_caso_positivo_lineas_independientes_reordenadas():
    """Caso positivo 2: funciones con sentencias independientes en distinto orden.

    Al reordenar dos llamadas independientes (con parámetros previamente definidos),
    la similitud con trigramas se mantiene alta (> 75%), clasificándolas como candidatas.
    """
    f1 = (
        "def registrar(a, b):\n"
        "    print(a)\n"
        "    print(b)\n"
        "    return a + b\n"
    )
    f2 = (
        "def registrar(a, b):\n"
        "    print(b)\n"
        "    print(a)\n"
        "    return a + b\n"
    )
    tokens_1 = _tokens_de_codigo(f1)
    tokens_2 = _tokens_de_codigo(f2)

    score_n3 = similitud_jaccard(tokens_1, tokens_2, n=3)

    # Con n=3, comparten la inmensa mayoría de los trigramas sintácticos
    assert score_n3 >= 0.75
    assert es_candidato_duplicado(score_n3, umbral=0.75) is True


def test_ejemplos_reales_positivos_del_repositorio():
    """Verifica que sumar_elementos y acumular_valores sean detectadas como duplicados al 100%."""
    directorio = Path(__file__).resolve().parent.parent / "ejemplos"
    funciones = {
        f.nombre: serializar_ast(normalizar_ast(f.nodo_ast))
        for f in extraer_funciones_directorio(directorio)
    }

    score = similitud_jaccard(funciones["sumar_elementos"], funciones["acumular_valores"], n=3)
    assert score == 1.0
    assert es_candidato_duplicado(score, umbral=0.75) is True


# ==============================================================================
# D. Casos negativos del Trabajo Práctico
# ==============================================================================


def test_caso_negativo_operacion_simple_vs_bucle():
    """Caso negativo 1: verificación simple de paridad vs cálculo de factorial con bucle."""
    directorio = Path(__file__).resolve().parent.parent / "ejemplos"
    funciones = {
        f.nombre: serializar_ast(normalizar_ast(f.nodo_ast))
        for f in extraer_funciones_directorio(directorio)
    }

    score = similitud_jaccard(funciones["es_par"], funciones["calcular_factorial"], n=3)

    # Deben compartir muy pocos trigramas y quedar muy por debajo del umbral del 75%
    assert score < 0.20
    assert es_candidato_duplicado(score, umbral=0.75) is False


def test_caso_negativo_suma_acumulada_vs_paridad():
    """Caso negativo 2: suma acumulada en lista vs verificación booleana de paridad."""
    directorio = Path(__file__).resolve().parent.parent / "ejemplos"
    funciones = {
        f.nombre: serializar_ast(normalizar_ast(f.nodo_ast))
        for f in extraer_funciones_directorio(directorio)
    }

    score = similitud_jaccard(funciones["sumar_elementos"], funciones["es_par"], n=3)

    # Score significativamente bajo (< 10%)
    assert score < 0.10
    assert es_candidato_duplicado(score, umbral=0.75) is False


def test_caso_negativo_suma_vs_factorial():
    """Caso negativo 3: suma acumulada vs bucle factorial con raise condicional."""
    directorio = Path(__file__).resolve().parent.parent / "ejemplos"
    funciones = {
        f.nombre: serializar_ast(normalizar_ast(f.nodo_ast))
        for f in extraer_funciones_directorio(directorio)
    }

    score = similitud_jaccard(funciones["sumar_elementos"], funciones["calcular_factorial"], n=3)

    assert score < 0.25
    assert es_candidato_duplicado(score, umbral=0.75) is False


# ==============================================================================
# E. Pruebas del umbral y candidatos a duplicado
# ==============================================================================


def test_umbral_evaluaciones():
    """Verifica las respuestas booleanas frente al umbral."""
    # Superior al umbral
    assert es_candidato_duplicado(0.80, umbral=0.75) is True

    # Exactamente igual al umbral
    assert es_candidato_duplicado(0.75, umbral=0.75) is True

    # Inferior al umbral
    assert es_candidato_duplicado(0.74, umbral=0.75) is False
    assert es_candidato_duplicado(0.00, umbral=0.75) is False


@pytest.mark.parametrize("umbral_invalido", [-0.1, 1.01, -5.0, 2.0])
def test_umbral_fuera_de_rango(umbral_invalido):
    """Comprueba que umbrales fuera de [0.0, 1.0] lancen ValueError."""
    with pytest.raises(ValueError, match="umbral debe estar comprendido entre 0.0 y 1.0"):
        es_candidato_duplicado(0.5, umbral=umbral_invalido)


@pytest.mark.parametrize("score_invalido", [-0.01, 1.05, 5.0])
def test_score_fuera_de_rango(score_invalido):
    """Comprueba que scores fuera de [0.0, 1.0] lancen ValueError."""
    with pytest.raises(ValueError, match="score debe estar comprendido entre 0.0 y 1.0"):
        es_candidato_duplicado(score=score_invalido, umbral=0.75)
