"""Motor de búsqueda de funciones similares vía AST.

Coordina la extracción, normalización, serialización y cálculo de similitud
para encontrar y rankear las funciones más similares a una función objetivo.

Uso principal:
    resultados = buscar_similares(directorio="./mi_repo", funcion="archivo.py:mi_funcion", top_k=5)
    reporte = ejecutar_busqueda(directorio="./mi_repo", funcion="archivo.py:mi_funcion")
"""

from dataclasses import dataclass
from pathlib import Path

from motor_ast.extractor import FuncionExtraida, extraer_funciones_directorio
from motor_ast.normalizador import normalizar_ast
from motor_ast.serializador import serializar_ast
from motor_ast.similitud import es_candidato_duplicado, similitud_jaccard


@dataclass
class ResultadoSimilitud:
    """Resultado individual de comparación de una función candidata con la objetivo."""

    nombre: str
    archivo: Path
    linea: int
    score: float
    es_duplicado: bool


@dataclass
class ReporteBusqueda:
    """Reporte completo con metadatos y resultados de una búsqueda Top-K."""

    directorio: Path
    funcion_objetivo: FuncionExtraida
    total_encontradas: int
    total_comparadas: int
    resultados: list[ResultadoSimilitud]
    umbral: float
    n: int
    top_k: int


def _resolver_archivo(
    parte_archivo: str,
    directorio: Path | None,
    archivos_disponibles: set[Path],
) -> Path:
    """Resuelve la ruta de un archivo admitiendo rutas relativas, absolutas o por nombre.

    Lanza:
        FileNotFoundError: Si no se encuentra el archivo en el conjunto disponible.
        ValueError: Si la referencia es ambigua (múltiples archivos con igual nombre).
    """
    path_solicitado = Path(parte_archivo)

    # 1. Coincidencia directa como ruta absoluta o relativa al CWD
    p_directo = path_solicitado.resolve()
    if p_directo in archivos_disponibles:
        return p_directo

    # 2. Coincidencia relativa al directorio del repositorio
    if directorio is not None:
        p_rel = (directorio / path_solicitado).resolve()
        if p_rel in archivos_disponibles:
            return p_rel

    # 3. Coincidencia por nombre de archivo o sufijo relativo
    coincidentes = [
        p for p in archivos_disponibles
        if p.name == path_solicitado.name or p.as_posix().endswith(path_solicitado.as_posix())
    ]

    if len(coincidentes) == 1:
        return coincidentes[0]
    if len(coincidentes) > 1:
        rutas_str = ", ".join(p.as_posix() for p in coincidentes)
        raise ValueError(
            f"Ruta ambigua: múltiples archivos coinciden con '{parte_archivo}' ({rutas_str}). "
            "Especifique la ruta relativa completa."
        )

    raise FileNotFoundError(
        f"No se encontró el archivo '{parte_archivo}' dentro del repositorio."
    )


def identificar_funcion_objetivo(
    funciones: list[FuncionExtraida],
    referencia: str,
    directorio: str | Path | None = None,
) -> FuncionExtraida:
    """Localiza de manera inequívoca la función objetivo a partir de 'archivo.py:nombre'.

    Parámetros:
        funciones: Lista de funciones extraídas en el repositorio.
        referencia: Cadena con formato 'archivo.py:nombre_funcion'.
        directorio: Ruta raíz del repositorio para resolver rutas relativas.

    Retorna:
        La instancia única de FuncionExtraida correspondiente.

    Lanza:
        ValueError: Si el formato es inválido, no se encuentra la función o hay ambigüedad.
        FileNotFoundError: Si el archivo no existe en el repositorio.
    """
    if ":" not in referencia:
        raise ValueError(
            f"Formato de función inválido '{referencia}'. "
            "Debe tener el formato 'archivo.py:nombre_funcion'"
        )

    parte_archivo, _, nombre_funcion = referencia.rpartition(":")
    parte_archivo = parte_archivo.strip()
    nombre_funcion = nombre_funcion.strip()

    if not parte_archivo or not nombre_funcion:
        raise ValueError(
            f"Formato de función inválido '{referencia}'. "
            "Debe tener el formato 'archivo.py:nombre_funcion'"
        )

    dir_path = Path(directorio).resolve() if directorio is not None else None
    archivos_disponibles = {f.archivo.resolve() for f in funciones}

    archivo_resuelto = _resolver_archivo(parte_archivo, dir_path, archivos_disponibles)

    coincidentes = [
        f for f in funciones
        if f.archivo.resolve() == archivo_resuelto and f.nombre == nombre_funcion
    ]

    if len(coincidentes) == 0:
        raise ValueError(
            f"No se encontró la función '{nombre_funcion}' en el archivo '{parte_archivo}'."
        )
    if len(coincidentes) > 1:
        lineas = ", ".join(str(f.linea) for f in coincidentes)
        raise ValueError(
            f"Referencia ambigua: se encontraron {len(coincidentes)} funciones con el "
            f"nombre '{nombre_funcion}' en '{parte_archivo}' (líneas: {lineas})."
        )

    return coincidentes[0]


def ejecutar_busqueda(
    directorio: str | Path,
    funcion: str,
    top_k: int = 5,
    umbral: float = 0.75,
    n: int = 3,
) -> ReporteBusqueda:
    """Ejecuta el pipeline completo de búsqueda de funciones similares vía AST.

    Parámetros:
        directorio: Ruta al repositorio local con archivos Python.
        funcion: Identificador de la función objetivo ('archivo.py:mi_funcion').
        top_k: Cantidad máxima de resultados a devolver (entero >= 1, por defecto 5).
        umbral: Umbral de similitud para clasificar candidatos a duplicado (por defecto 0.75).
        n: Tamaño de los n-gramas para Jaccard (por defecto 3).

    Retorna:
        ReporteBusqueda estructurado con metadatos y lista de resultados ordenados.

    Lanza:
        FileNotFoundError: Si el directorio o archivo no existe.
        NotADirectoryError: Si la ruta no es una carpeta.
        ValueError: Si los parámetros son inválidos o no se encuentra la función.
    """
    if not isinstance(top_k, int) or top_k < 1:
        raise ValueError(f"top_k debe ser un entero positivo >= 1, recibido: {top_k}")
    if not (0.0 <= umbral <= 1.0):
        raise ValueError(f"El umbral debe estar comprendido entre 0.0 y 1.0, recibido: {umbral}")
    if not isinstance(n, int) or n < 1:
        raise ValueError(f"El tamaño de n-grama n debe ser un entero positivo >= 1, recibido: {n}")

    dir_path = Path(directorio)
    funciones = extraer_funciones_directorio(dir_path)

    if not funciones:
        raise ValueError(f"No se encontraron funciones Python en el directorio '{dir_path}'.")

    objetivo = identificar_funcion_objetivo(funciones, funcion, dir_path)

    # 1. Normalizar y serializar cada función exactamente una vez (precomputación)
    preparadas = [
        (f, serializar_ast(normalizar_ast(f.nodo_ast)))
        for f in funciones
    ]

    # 2. Localizar los tokens de la función objetivo
    tokens_objetivo = next(
        tokens for f, tokens in preparadas
        if (f.archivo.resolve(), f.linea) == (objetivo.archivo.resolve(), objetivo.linea)
    )

    # 3. Comparar con las demás funciones (excluyendo la función objetivo por identidad)
    resultados: list[ResultadoSimilitud] = []
    total_comparadas = 0

    for f, tokens_candidata in preparadas:
        if (f.archivo.resolve(), f.linea) == (objetivo.archivo.resolve(), objetivo.linea):
            continue

        total_comparadas += 1
        score = similitud_jaccard(tokens_objetivo, tokens_candidata, n=n)
        es_duplicado = es_candidato_duplicado(score, umbral=umbral)

        resultados.append(
            ResultadoSimilitud(
                nombre=f.nombre,
                archivo=f.archivo,
                linea=f.linea,
                score=score,
                es_duplicado=es_duplicado,
            )
        )

    # 4. Ordenar resultados: primero por score descendente; desempate determinista por ruta, nombre y línea
    resultados.sort(
        key=lambda r: (-r.score, r.archivo.as_posix(), r.nombre, r.linea)
    )

    # 5. Tomar los Top-K resultados
    top_resultados = resultados[:top_k]

    return ReporteBusqueda(
        directorio=dir_path,
        funcion_objetivo=objetivo,
        total_encontradas=len(funciones),
        total_comparadas=total_comparadas,
        resultados=top_resultados,
        umbral=umbral,
        n=n,
        top_k=top_k,
    )


def buscar_similares(
    directorio: str | Path,
    funcion: str,
    top_k: int = 5,
    umbral: float = 0.75,
    n: int = 3,
) -> list[ResultadoSimilitud]:
    """Busca y devuelve las funciones más similares a la función consultada.

    Convenience wrapper sobre ejecutar_busqueda que devuelve directamente
    la lista de ResultadoSimilitud.
    """
    reporte = ejecutar_busqueda(
        directorio=directorio,
        funcion=funcion,
        top_k=top_k,
        umbral=umbral,
        n=n,
    )
    return reporte.resultados
