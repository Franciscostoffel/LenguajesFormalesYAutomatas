# Motor de búsqueda de funciones similares vía AST

Trabajo práctico de **Lenguajes Formales y Autómatas**, Ingeniería Informática,
Universidad Católica de Santiago del Estero (UCSE), 2026.

---

## 1. Objetivo y Fundamento Teórico

El objetivo de esta herramienta es encontrar funciones estructuralmente similares en
repositorios locales de código Python, incluso cuando cambien los nombres de variables,
parámetros o valores literales.

El sistema modela el principio detrás de herramientas de detección de código duplicado
y plagio (como SonarQube, PMD/CPD, MOSS o JPlag):

1. **El AST como árbol de derivación:** Al parsear código Python con `ast.parse()`, se
   obtiene un Árbol de Sintaxis Abstracta (AST) que representa formalmente la estructura
   gramatical de cada función.
2. **Comparación sintáctica vs texto plano:** En lugar de comparar cadenas de caracteres
   (sensibles a espacios, comentarios o renombres), se comparan representaciones derivadas
   de los árboles de sintaxis.
3. **Flujo completo:**
   ```text
   Archivos .py ──> Extracción ──> Normalización ──> Serialización ──> Similitud Jaccard ──> Ranking Top-K
   ```

---

## 2. Instalación y Requisitos

Requiere **Python 3.10** o superior. Utiliza exclusivamente la biblioteca estándar de Python
para el procesamiento sintáctico y el cálculo de métricas. La única dependencia externa de
desarrollo es `pytest` para la suite de pruebas automatizadas.

### Configuración del entorno virtual

En PowerShell (Windows):

```powershell
# 1. Crear el entorno virtual
python -m venv .venv

# 2. Activar el entorno virtual
.\.venv\Scripts\Activate.ps1

# 3. Instalar dependencias de desarrollo
python -m pip install -r requirements.txt
```

En Linux / macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## 3. Uso de la Interfaz de Línea de Comandos (CLI)

El punto de entrada principal es `buscar_similares.py`.

### Sintaxis básica

```bash
python buscar_similares.py --dir <directorio> --funcion <archivo.py:nombre_funcion> [opciones]
```

### Argumentos disponibles

| Argumento | Tipo | Obligatorio | Por defecto | Descripción |
| :--- | :---: | :---: | :---: | :--- |
| `--dir` | Ruta | **Sí** | - | Ruta al repositorio o carpeta con archivos `.py`. |
| `--funcion` | Texto | **Sí** | - | Función objetivo a buscar en formato `archivo.py:nombre_funcion`. |
| `--top` | Entero | No | `5` | Cantidad máxima de resultados a mostrar en el ranking. |
| `--umbral` | Decimal | No | `0.75` | Umbral de similitud para clasificar como candidata a duplicado. |
| `--n` | Entero | No | `3` | Tamaño de los n-gramas en la métrica de Jaccard (trigramas). |

---

## 4. Ejemplos de Ejecución

Todos los ejemplos pueden ejecutarse desde la raíz del proyecto sobre la carpeta `ejemplos/`:

### Búsqueda estándar (Top 5 con trigramas y umbral al 75%)

```powershell
python buscar_similares.py --dir ./ejemplos --funcion funciones_similares.py:sumar_elementos --top 5
```

**Salida en consola:**

```text
========================================
 MOTOR DE BÚSQUEDA DE FUNCIONES VIA AST
========================================

Repositorio: ./ejemplos
Función objetivo: funciones_similares.py:sumar_elementos

Métrica: Jaccard
N-gramas: 3
Umbral: 75%
Top solicitado: 5

----------------------------------------
RESULTADOS
----------------------------------------

1. acumular_valores
   Archivo: funciones_similares.py
   Línea: 12
   Similitud: 100.00%
   Candidata a duplicado: SÍ

2. calcular_factorial
   Archivo: funciones_distintas.py
   Línea: 9
   Similitud: 20.34%
   Candidata a duplicado: NO

3. es_par
   Archivo: funciones_distintas.py
   Línea: 4
   Similitud: 4.76%
   Candidata a duplicado: NO

----------------------------------------
Funciones encontradas: 4
Funciones comparadas: 3
Resultados mostrados: 3
========================================
```

### Modificando el Top-K (Top 1)

```powershell
python buscar_similares.py --dir ./ejemplos --funcion funciones_similares.py:sumar_elementos --top 1
```

### Modificando el umbral de duplicado (`--umbral 0.90`)

```powershell
python buscar_similares.py --dir ./ejemplos --funcion funciones_similares.py:sumar_elementos --umbral 0.90
```

### Modificando el tamaño de los n-gramas (`--n 2`, bigramas)

```powershell
python buscar_similares.py --dir ./ejemplos --funcion funciones_similares.py:sumar_elementos --n 2
```

---

## 5. Estructura del Proyecto

```text
LenguajesFormalesYAutomatas/
├── buscar_similares.py            # Punto de entrada CLI con argparse
├── motor_ast/                     # Paquete principal modular
│   ├── __init__.py
│   ├── extractor.py               # Extracción recursiva de funciones y AST
│   ├── normalizador.py            # Homogeneización de variables (VARx) y literales (LIT)
│   ├── serializador.py            # Recorrido pre-order y generación determinista de tokens
│   ├── similitud.py               # N-gramas y coeficiente de similitud de Jaccard
│   └── buscador.py                # Coordinador de búsqueda, resolución y ranking Top-K
├── tests/                         # Suite completa de pruebas con pytest (124 tests)
│   ├── __init__.py
│   ├── test_casos_tp.py           # 4 casos de integración del TP (2 positivos, 2 negativos)
│   ├── test_extractor.py          # Pruebas de extracción y manejo de errores (18 tests)
│   ├── test_normalizador.py       # Pruebas de transformación AST e inmutabilidad (26 tests)
│   ├── test_serializador.py       # Pruebas de recorrido pre-order y tokens (15 tests)
│   ├── test_similitud.py          # Pruebas de Jaccard, casos positivos y negativos (35 tests)
│   └── test_buscador.py           # Pruebas de ranking, resolución y CLI (27 tests)
├── ejemplos/                      # Funciones de prueba para demostraciones
│   ├── funciones_similares.py     # Clones con variables y parámetros renombrados
│   └── funciones_distintas.py     # Funciones con estructuras sintácticas disímiles
├── docs/
│   └── decisiones_diseno.md       # Documento exhaustivo de fundamentación y diseño
├── requirements.txt
├── .gitignore
└── README.md
```

---

## 6. Ejecución de Pruebas Automatizadas

Para ejecutar la suite completa de pruebas unitarias (124 tests en total):

```powershell
python -m pytest -v
```

Para ejecutar los 4 casos de integración solicitados en el enunciado:

```powershell
python -m pytest tests/test_casos_tp.py -v
```

Para ejecutar pruebas de un módulo específico:

```powershell
python -m pytest tests/test_buscador.py -v
python -m pytest tests/test_similitud.py -v
python -m pytest tests/test_serializador.py -v
python -m pytest tests/test_normalizador.py -v
python -m pytest tests/test_extractor.py -v
```

---

## 7. Limitaciones Conocidas

1. **Granularidad de función:** El análisis se realiza entre funciones individuales, no a nivel de clases completas ni similitud inter-módulos.
2. **Reordenamiento extenso:** Si bien tolera reordenamientos locales leves de instrucciones independientes, intercambiar bloques grandes de código quiebra los n-gramas en las fronteras y reduce el puntaje.
3. **Clones semánticos (Tipo 4):** Funciones que resuelven el mismo problema con algoritmos completamente distintos (por ejemplo, iteración vs recursión o fórmulas cerradas) generan ASTs diferentes y no se detectan como similares.
4. **Similitud estructural no garantiza equivalencia semántica:** Dos funciones pueden compartir una estructura idéntica realizando tareas distintas; los resultados deben interpretarse como *candidatas a duplicado* para su revisión.
