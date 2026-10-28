"""Cálculo de similitud estructural entre secuencias de tokens del AST mediante Jaccard.

Aplica la métrica de Jaccard sobre n-gramas de tokens obtenidos tras la
normalización y serialización de funciones Python.

Uso principal:
    score = similitud_jaccard(tokens_a, tokens_b, n=3)
    es_duplicado = es_candidato_duplicado(score, umbral=0.75)

Flujo del motor:
    extractor -> normalizador -> serializador -> similitud -> (buscador)

Para ver una demostración desde la raíz del proyecto:
    python -m motor_ast.similitud
"""

from typing import Sequence


def generar_ngramas(tokens: Sequence[str], n: int = 3) -> set[tuple[str, ...]]:
    """Genera el conjunto de n-gramas consecutivos a partir de una secuencia de tokens.

    Un n-grama es una tupla de n tokens contiguos que captura el contexto sintáctico
    local. Se devuelve un conjunto (set) para su uso en la métrica de Jaccard.

    Comportamiento con secuencias cortas:
        - Si la secuencia está vacía, devuelve un conjunto vacío: set().
        - Si la secuencia tiene entre 1 y n-1 tokens (no vacía pero menor a n),
          se representa como un único n-grama con todos los tokens disponibles,
          evitando descartar funciones breves.

    Parámetros:
        tokens: Lista o tupla de tokens sintácticos generados por el serializador.
        n: Longitud de cada n-grama (entero positivo >= 1, por defecto 3).

    Lanza:
        ValueError: Si n no es un entero mayor o igual a 1.
    """
    if not isinstance(n, int) or n < 1:
        raise ValueError(f"El tamaño de n-grama n debe ser un entero positivo >= 1, recibido: {n}")

    longitud = len(tokens)
    if longitud == 0:
        return set()

    if longitud < n:
        return {tuple(tokens)}

    return {tuple(tokens[i : i + n]) for i in range(longitud - n + 1)}


def similitud_jaccard(tokens_a: Sequence[str], tokens_b: Sequence[str], n: int = 3) -> float:
    """Calcula la similitud de Jaccard entre los n-gramas de dos secuencias de tokens.

    Fórmula:
        J(A, B) = |A ∩ B| / |A ∪ B|

    Casos límite:
        - Ambas secuencias vacías: similitud 1.0 (idénticas por vacuidad).
        - Una vacía y la otra no: similitud 0.0.
        - Secuencias idénticas: similitud 1.0.
        - Sin ningún n-grama compartido: similitud 0.0.

    La métrica es conmutativa/simétrica:
        similitud_jaccard(A, B) == similitud_jaccard(B, A)

    Parámetros:
        tokens_a: Secuencia de tokens de la primera función.
        tokens_b: Secuencia de tokens de la segunda función.
        n: Longitud de los n-gramas (por defecto 3).

    Retorna:
        Puntaje float en el intervalo [0.0, 1.0].
    """
    if not tokens_a and not tokens_b:
        return 1.0
    if not tokens_a or not tokens_b:
        return 0.0

    ngramas_a = generar_ngramas(tokens_a, n=n)
    ngramas_b = generar_ngramas(tokens_b, n=n)

    union = ngramas_a | ngramas_b
    if not union:
        return 1.0

    interseccion = ngramas_a & ngramas_b
    return len(interseccion) / len(union)


def es_candidato_duplicado(score: float, umbral: float = 0.75) -> bool:
    """Indica si una puntuación de similitud alcanza o supera el umbral configurado.

    Parámetros:
        score: Puntaje de similitud en el intervalo [0.0, 1.0].
        umbral: Valor límite configurable en [0.0, 1.0] (por defecto 0.75).

    Retorna:
        True si score >= umbral, False en caso contrario.

    Lanza:
        ValueError: Si score o umbral están fuera del intervalo [0.0, 1.0].
    """
    if not (0.0 <= umbral <= 1.0):
        raise ValueError(f"El umbral debe estar comprendido entre 0.0 y 1.0, recibido: {umbral}")
    if not (0.0 <= score <= 1.0):
        raise ValueError(f"El score debe estar comprendido entre 0.0 y 1.0, recibido: {score}")

    return score >= umbral


def _demostrar_similitud() -> None:
    """Ejecuta una demostración comparando funciones reales de los ejemplos del proyecto."""
    from pathlib import Path

    from motor_ast.extractor import extraer_funciones_directorio
    from motor_ast.normalizador import normalizar_ast
    from motor_ast.serializador import serializar_ast

    directorio = Path(__file__).resolve().parent.parent / "ejemplos"
    funciones = {
        f.nombre: serializar_ast(normalizar_ast(f.nodo_ast))
        for f in extraer_funciones_directorio(directorio)
    }

    pares_a_comparar = [
        ("sumar_elementos", "acumular_valores", "Caso positivo: funciones clonadas con variables renombradas"),
        ("sumar_elementos", "es_par", "Caso negativo: suma con acumulador vs verificación de paridad"),
        ("sumar_elementos", "calcular_factorial", "Caso negativo: suma vs factorial con validación y bucle"),
        ("es_par", "calcular_factorial", "Caso negativo: paridad simple vs bucle factorial"),
    ]

    umbral_defecto = 0.75
    n_defecto = 3

    print("=" * 60)
    print("DEMOSTRACIÓN DE SIMILITUD DE JACCARD SOBRE N-GRAMAS (AST)")
    print(f"Configuración: n={n_defecto} (trigramas) | Umbral: {umbral_defecto:.0%}")
    print("=" * 60)

    for nombre_a, nombre_b, descripcion in pares_a_comparar:
        if nombre_a not in funciones or nombre_b not in funciones:
            continue

        tokens_a = funciones[nombre_a]
        tokens_b = funciones[nombre_b]

        ng_a = generar_ngramas(tokens_a, n=n_defecto)
        ng_b = generar_ngramas(tokens_b, n=n_defecto)

        interseccion = ng_a & ng_b
        union = ng_a | ng_b

        score = similitud_jaccard(tokens_a, tokens_b, n=n_defecto)
        es_duplicado = es_candidato_duplicado(score, umbral=umbral_defecto)

        print(f"\n{descripcion.upper()}")
        print("-" * 60)
        print(f"Función A: {nombre_a}")
        print(f"Función B: {nombre_b}")
        print(f"Tokens A: {len(tokens_a)}")
        print(f"Tokens B: {len(tokens_b)}")
        print(f"N-gramas distintos A: {len(ng_a)}")
        print(f"N-gramas distintos B: {len(ng_b)}")
        print(f"N-gramas compartidos (intersección): {len(interseccion)}")
        print(f"N-gramas unión: {len(union)}")
        print(f"Similitud Jaccard: {score:.2%}")
        print(f"Umbral: {umbral_defecto:.2%}")
        resultado_str = "CANDIDATAS A DUPLICADO" if es_duplicado else "NO CANDIDATAS"
        print(f"Resultado: {resultado_str}")

    print("\n" + "=" * 60)
    print("COMPARATIVA DE EFECTO DE N (n=2 vs n=3 vs n=4)")
    print("=" * 60)
    print(f"{'Par de funciones':<35} | {'n=2':<8} | {'n=3':<8} | {'n=4':<8}")
    print("-" * 65)
    for nombre_a, nombre_b, _ in pares_a_comparar:
        if nombre_a not in funciones or nombre_b not in funciones:
            continue
        scores = [
            f"{similitud_jaccard(funciones[nombre_a], funciones[nombre_b], n=n_val):.2%}"
            for n_val in (2, 3, 4)
        ]
        etiqueta = f"{nombre_a} vs {nombre_b}"
        print(f"{etiqueta:<35} | {scores[0]:<8} | {scores[1]:<8} | {scores[2]:<8}")
    print("=" * 60)


if __name__ == "__main__":
    _demostrar_similitud()
