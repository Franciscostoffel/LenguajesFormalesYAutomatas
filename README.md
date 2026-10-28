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

Etapa 4: extractor, normalizador y serializador implementados.

### 1. Extractor (`motor_ast/extractor.py`)
Encuentra archivos `.py` recursivamente, los ordena por ruta relativa y extrae funciones
normales, asíncronas, anidadas y métodos de clases en orden de línea. Cada `FuncionExtraida`
conserva nombre, ruta, línea y nodo AST original. No ejecuta el código ni modifica los
archivos o sus árboles.

Para ejecutar la demostración del extractor:

```powershell
python -m motor_ast.extractor
```

### 2. Normalizador (`motor_ast/normalizador.py`)
Devuelve una copia independiente, fija el nombre raíz en `FUNC`, reemplaza nombres simples
por `VAR1`, `VAR2`, etc., y números y cadenas por el string `LIT` dentro de nodos `Constant`.
Los parámetros se registran primero; los demás nombres siguen el orden de visita. Conserva
operadores, estructuras y atributos como `.metodo`. Reinicia el diccionario en cada llamada.

Para ver la demostración del normalizador:

```powershell
python -m motor_ast.normalizador
```

### 3. Serializador (`motor_ast/serializador.py`)
Recorre el AST normalizado en pre-order usando `ast.iter_child_nodes()`, generando una
secuencia lineal y determinista de tokens (`FunctionDef`, `arguments`, `arg:VAR1`,
`BinOp`, `Add`, `Constant:LIT`, etc.). Preserva operadores, estructuras de control y la
correspondencia de variables y literales.

Para ver la demostración del serializador:

```powershell
python -m motor_ast.serializador
```

### Pruebas automatizadas

Para ejecutar todas las pruebas unitarias:

```powershell
python -m pytest -v
```

La similitud, búsqueda y CLI definitiva **no están implementadas**.
Ejecutar `buscar_similares.py` todavía no realiza una búsqueda.
Las decisiones pendientes están en [docs/decisiones_diseno.md](docs/decisiones_diseno.md).
