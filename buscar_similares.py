#!/usr/bin/env python3
"""Interfaz de línea de comandos (CLI) para el motor de búsqueda de funciones similares vía AST.

Permite buscar qué funciones de un repositorio local son estructuralmente
similares a una función objetivo dada, ordenadas por puntaje de similitud Top-K.

Uso:
    python buscar_similares.py --dir ./mi_repo --funcion archivo.py:mi_funcion --top 5
"""

import argparse
from pathlib import Path
import sys

from motor_ast.buscador import ReporteBusqueda, ejecutar_busqueda


def crear_parser() -> argparse.ArgumentParser:
    """Configura los argumentos de línea de comandos del buscador."""
    parser = argparse.ArgumentParser(
        description="Motor de búsqueda de funciones similares en repositorios Python vía AST."
    )
    parser.add_argument(
        "--dir",
        dest="directorio",
        required=True,
        help="Ruta al repositorio o carpeta que contiene los archivos .py a analizar.",
    )
    parser.add_argument(
        "--funcion",
        required=True,
        help="Función objetivo a comparar con formato 'archivo.py:nombre_funcion'.",
    )
    parser.add_argument(
        "--top",
        dest="top_k",
        type=int,
        default=5,
        help="Cantidad máxima de resultados a mostrar (Top-K, por defecto 5).",
    )
    parser.add_argument(
        "--umbral",
        type=float,
        default=0.75,
        help="Umbral de similitud para clasificar candidatos a duplicado (por defecto 0.75).",
    )
    parser.add_argument(
        "--n",
        dest="n",
        type=int,
        default=3,
        help="Tamaño de los n-gramas utilizados en la métrica Jaccard (por defecto 3).",
    )
    return parser


def formatear_reporte(reporte: ReporteBusqueda) -> str:
    """Genera la presentación textual en terminal de los resultados de búsqueda."""
    lineas = [
        "=" * 40,
        " MOTOR DE BÚSQUEDA DE FUNCIONES VIA AST",
        "=" * 40,
        "",
        f"Repositorio: {reporte.directorio}",
        f"Función objetivo: {reporte.funcion_objetivo.archivo.name}:{reporte.funcion_objetivo.nombre}",
        "",
        "Métrica: Jaccard",
        f"N-gramas: {reporte.n}",
        f"Umbral: {reporte.umbral:.0%}",
        f"Top solicitado: {reporte.top_k}",
        "",
        "-" * 40,
        "RESULTADOS",
        "-" * 40,
    ]

    if not reporte.resultados:
        lineas.append("\nNo se encontraron otras funciones para comparar en el repositorio.\n")
    else:
        for idx, res in enumerate(reporte.resultados, start=1):
            duplicado_str = "SÍ" if res.es_duplicado else "NO"
            # Mostrar la ruta relativa al repositorio si es posible para mejor lectura
            try:
                ruta_mostrar = res.archivo.resolve().relative_to(reporte.directorio.resolve())
            except ValueError:
                ruta_mostrar = res.archivo.name

            lineas.extend([
                f"\n{idx}. {res.nombre}",
                f"   Archivo: {ruta_mostrar}",
                f"   Línea: {res.linea}",
                f"   Similitud: {res.score:.2%}",
                f"   Candidata a duplicado: {duplicado_str}",
            ])
        lineas.append("")

    lineas.extend([
        "-" * 40,
        f"Funciones encontradas: {reporte.total_encontradas}",
        f"Funciones comparadas: {reporte.total_comparadas}",
        f"Resultados mostrados: {len(reporte.resultados)}",
        "=" * 40,
    ])

    return "\n".join(lineas)


def main(argv: list[str] | None = None) -> int:
    """Punto de entrada principal de la CLI."""
    parser = crear_parser()
    args = parser.parse_args(argv)

    try:
        reporte = ejecutar_busqueda(
            directorio=args.directorio,
            funcion=args.funcion,
            top_k=args.top_k,
            umbral=args.umbral,
            n=args.n,
        )
        print(formatear_reporte(reporte))
        return 0
    except (FileNotFoundError, NotADirectoryError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    except Exception as error:
        print(f"Error inesperado: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
