"""Suite de pruebas de integración exigidas por el trabajo práctico.

Contiene exactamente cuatro casos de prueba de integración integral:
- 2 casos positivos: variables renombradas y líneas reordenadas.
- 2 casos negativos: funciones estructuralmente diferentes y algoritmos distintos.

Cada prueba recorre el flujo completo del sistema:
Extracción -> Normalización -> Serialización -> Similitud Jaccard -> Buscador Top-K.
"""

from motor_ast.buscador import ejecutar_busqueda


def test_caso_positivo_1_variables_renombradas(tmp_path):
    """TEST 1 (Positivo): Funciones idénticas salvo renombramiento de variables y parámetros.

    sumar(a, b) vs calcular(x, y):
    - ASTs normalizados equivalentes.
    - Secuencias de tokens idénticas.
    - Similitud de Jaccard esperada: 1.0 (100%).
    - Clasificación: Candidata a duplicado (SÍ).
    """
    archivo_a = tmp_path / "modulo_a.py"
    archivo_b = tmp_path / "modulo_b.py"

    archivo_a.write_text(
        "def sumar(a, b):\n"
        "    resultado = a + b\n"
        "    return resultado\n",
        encoding="utf-8",
    )
    archivo_b.write_text(
        "def calcular(x, y):\n"
        "    total = x + y\n"
        "    return total\n",
        encoding="utf-8",
    )

    reporte = ejecutar_busqueda(
        directorio=tmp_path,
        funcion="modulo_a.py:sumar",
        top_k=5,
        umbral=0.75,
        n=3,
    )

    # 1. Metadatos de la búsqueda
    assert reporte.total_encontradas == 2
    assert reporte.total_comparadas == 1
    assert len(reporte.resultados) == 1

    # 2. Exclusión de la función objetivo
    assert reporte.funcion_objetivo.nombre == "sumar"
    assert all(r.nombre != "sumar" for r in reporte.resultados)

    # 3. Resultado de la comparación
    resultado = reporte.resultados[0]
    assert resultado.nombre == "calcular"
    assert resultado.archivo.name == "modulo_b.py"
    assert resultado.score == 1.0
    assert resultado.es_duplicado is True


def test_caso_positivo_2_lineas_reordenadas(tmp_path):
    """TEST 2 (Positivo): Funciones con instrucciones independientes reordenadas.

    procesar(a, b, c) vs calcular(a, b, c):
    - Contienen tres asignaciones independientes donde las dos primeras se permutan.
    - Comparten la amplia mayoría de los trigramas sintácticos normalizados (> 75%).
    - Similitud esperada: ~81.40%.
    - Clasificación: Candidata a duplicado (SÍ).
    """
    archivo = tmp_path / "operaciones.py"
    archivo.write_text(
        "def procesar(a, b, c):\n"
        "    x = a + b\n"
        "    y = b * c\n"
        "    z = a - c\n"
        "    return x + y + z\n"
        "\n"
        "def calcular(a, b, c):\n"
        "    y = b * c\n"
        "    x = a + b\n"
        "    z = a - c\n"
        "    return x + y + z\n",
        encoding="utf-8",
    )

    reporte = ejecutar_busqueda(
        directorio=tmp_path,
        funcion="operaciones.py:procesar",
        top_k=5,
        umbral=0.75,
        n=3,
    )

    assert reporte.total_encontradas == 2
    assert reporte.total_comparadas == 1
    assert len(reporte.resultados) == 1

    resultado = reporte.resultados[0]
    assert resultado.nombre == "calcular"
    assert resultado.score >= 0.75
    assert round(resultado.score, 4) == 0.8140
    assert resultado.es_duplicado is True


def test_caso_negativo_1_estructuralmente_diferentes(tmp_path):
    """TEST 3 (Negativo): Operación aritmética simple vs bucle for con condicional.

    sumar(a, b) vs contar_pares(numeros):
    - Estructuras sintácticas completamente disímiles.
    - Similitud esperada: muy baja (~2.86%).
    - Clasificación: NO candidata a duplicado.
    """
    archivo = tmp_path / "distintas.py"
    archivo.write_text(
        "def sumar(a, b):\n"
        "    return a + b\n"
        "\n"
        "def contar_pares(numeros):\n"
        "    contador = 0\n"
        "    for numero in numeros:\n"
        "        if numero % 2 == 0:\n"
        "            contador += 1\n"
        "    return contador\n",
        encoding="utf-8",
    )

    reporte = ejecutar_busqueda(
        directorio=tmp_path,
        funcion="distintas.py:sumar",
        top_k=5,
        umbral=0.75,
        n=3,
    )

    assert reporte.total_encontradas == 2
    assert reporte.total_comparadas == 1
    assert len(reporte.resultados) == 1

    resultado = reporte.resultados[0]
    assert resultado.nombre == "contar_pares"
    assert resultado.score < 0.10
    assert round(resultado.score, 4) == 0.0286
    assert resultado.es_duplicado is False


def test_caso_negativo_2_algoritmos_distintos(tmp_path):
    """TEST 4 (Negativo): Inversión con slicing vs búsqueda secuencial con bucle.

    invertir_lista(lista) vs buscar_elemento(lista, objetivo):
    - Nodos AST diferentes (Subscript/Slice vs For/If/Compare).
    - Similitud esperada: muy baja (~3.70%).
    - Clasificación: NO candidata a duplicado.
    """
    archivo = tmp_path / "algoritmos.py"
    archivo.write_text(
        "def invertir_lista(lista):\n"
        "    return lista[::-1]\n"
        "\n"
        "def buscar_elemento(lista, objetivo):\n"
        "    for elemento in lista:\n"
        "        if elemento == objetivo:\n"
        "            return True\n"
        "    return False\n",
        encoding="utf-8",
    )

    reporte = ejecutar_busqueda(
        directorio=tmp_path,
        funcion="algoritmos.py:invertir_lista",
        top_k=5,
        umbral=0.75,
        n=3,
    )

    assert reporte.total_encontradas == 2
    assert reporte.total_comparadas == 1
    assert len(reporte.resultados) == 1

    resultado = reporte.resultados[0]
    assert resultado.nombre == "buscar_elemento"
    assert resultado.score < 0.10
    assert round(resultado.score, 4) == 0.0370
    assert resultado.es_duplicado is False

