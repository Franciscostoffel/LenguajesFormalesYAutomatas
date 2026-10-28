# Motor de búsqueda de funciones similares vía AST

Trabajo práctico de Lenguajes Formales y Autómatas, Ingeniería Informática,
UCSE, 2026.

## Objetivo

Construir de manera incremental una herramienta Python que encuentre funciones
estructuralmente similares en repositorios locales pequeños o medianos, incluso
cuando cambien sus nombres de variables o sus valores literales.

## Qué es un AST

Un árbol de sintaxis abstracta (AST) representa la estructura sintáctica de un
programa mediante nodos, por ejemplo funciones, asignaciones y operaciones.
Omite detalles de escritura como espacios y comentarios. Se relaciona con los
árboles de derivación estudiados en la materia, pero simplifica la representación
de la sintaxis. Se utilizará `ast.parse()` de la biblioteca estándar de Python;
no se construirá un parser propio.

## Flujo previsto

Directorio con archivos `.py` → extracción de funciones y sus AST → normalización
de identificadores y literales → recorrido pre-order y secuencias de tokens →
comparación estructural → resultados ordenados para la función consultada.

Los tokens de esta serialización serán una representación del AST, no los tokens
léxicos del código fuente. La métrica de similitud todavía no fue elegida.

## Estructura

```text
LenguajesFormalesYAutomatas/
├── buscar_similares.py
├── motor_ast/
│   ├── __init__.py
│   ├── extractor.py
│   ├── normalizador.py
│   ├── serializador.py
│   ├── similitud.py
│   └── buscador.py
├── tests/
│   ├── __init__.py
│   ├── test_extractor.py
│   ├── test_normalizador.py
│   ├── test_serializador.py
│   ├── test_similitud.py
│   └── test_buscador.py
├── ejemplos/
│   ├── funciones_similares.py
│   └── funciones_distintas.py
├── docs/
│   └── decisiones_diseno.md
├── requirements.txt
├── .gitignore
└── README.md
```

## Entorno y pruebas

Se propone Python 3.10 o superior como base del proyecto. El procesamiento usará
la biblioteca estándar; `pytest` es la única dependencia de desarrollo inicial.

Desde la raíz del repositorio, en PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pytest
```

También se puede trabajar sin activar el entorno:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest
```

En Linux/macOS, la activación equivalente es `source .venv/bin/activate`.
Los archivos `__init__.py` definen los paquetes; ejecutar `python -m pytest`
desde la raíz permite importar los módulos sin instalar el proyecto.

## Estado actual

Etapa 2: extractor implementado en `motor_ast/extractor.py`, con pruebas en
`tests/test_extractor.py`. Encuentra archivos `.py` recursivamente, los ordena por
ruta relativa y extrae funciones normales, asíncronas, anidadas y métodos de clases
en orden de línea. Cada `FuncionExtraida` conserva nombre, ruta, línea y nodo AST
original. No ejecuta el código ni modifica los archivos o sus árboles.

El lector respeta la declaración de codificación del archivo mediante
`tokenize.open()`. Una ruta inexistente produce `FileNotFoundError` y una ruta que
no sea carpeta, `NotADirectoryError`. Ante errores de lectura, codificación o
sintaxis de un archivo, la extracción del directorio registra una advertencia con
su ruta y el error, lo omite y continúa con los demás. Los resultados pueden ser
parciales; si ningún archivo aporta funciones, devuelve una lista vacía.
`parsear_archivo()` sigue propagando sus errores cuando se usa individualmente.
No se excluyen carpetas en esta etapa; conviene
seleccionar una carpeta de fuentes, sin entornos virtuales dentro.

Para ejecutar la demostración real sobre `ejemplos/`, desde la raíz:

```powershell
python -m motor_ast.extractor
```

Muestra archivo, nombre, línea y tipo AST de cada función, y el total encontrado.
Para ejecutar solo las pruebas del extractor:

```powershell
python -m pytest tests/test_extractor.py -v
```

La normalización, serialización, similitud, búsqueda y CLI definitiva **no están
implementadas**. Ejecutar `buscar_similares.py` todavía no realiza una búsqueda.
Las decisiones pendientes están en [docs/decisiones_diseno.md](docs/decisiones_diseno.md).
