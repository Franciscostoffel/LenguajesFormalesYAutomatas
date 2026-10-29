# Decisiones de diseño — etapa 6 (Final)

## Arquitectura del sistema

Se separan las responsabilidades en módulos independientes y testeables del paquete `motor_ast`, coordinados por el punto de entrada CLI en la raíz del proyecto:

| Archivo | Responsabilidad implementada |
| --- | --- |
| `buscar_similares.py` | CLI principal con `argparse`: valida argumentos, ejecuta la búsqueda y formatea resultados. |
| `motor_ast/extractor.py` | Recorre archivos `.py`, parsea con `ast.parse()` y extrae funciones con metadatos (`FuncionExtraida`). |
| `motor_ast/normalizador.py` | Transforma ASTs para homogeneizar identificadores (`VAR1`, `VAR2`, ...) y literales (`LIT`). |
| `motor_ast/serializador.py` | Recorre el AST normalizado en pre-order produciendo secuencias lineales deterministas de tokens. |
| `motor_ast/similitud.py` | Genera n-gramas, calcula similitud de Jaccard y clasifica candidatos según el umbral. |
| `motor_ast/buscador.py` | Localiza la función objetivo, precomputa representaciones, rankea Top-K y excluye la función consultada. |

## Flujo de datos y fundamento teórico

```text
Repositorio local (.py)
        │
        ▼  (extractor.py)
Lista de FuncionExtraida (AST original + archivo + línea)
        │
        ▼  (buscador.py: identificar_funcion_objetivo)
Función objetivo identificada vs Funciones candidatas
        │
        ▼  (normalizador.py)
ASTs normalizados (copias independientes, nombres FUNC/VARx, literales LIT)
        │
        ▼  (serializador.py)
Secuencias lineales de tokens sintácticos (recorrido pre-order)
        │
        ▼  (similitud.py)
Conjuntos de n-gramas (trigramas) e índice de Jaccard |A ∩ B| / |A ∪ B|
        │
        ▼  (buscador.py: ejecutar_busqueda)
Ranking Top-K ordenado por similitud descendente (con desempate determinista)
        │
        ▼  (buscar_similares.py)
Salida estructurada y legible en terminal (CLI)
```

El AST es una abstracción del árbol de derivación sintáctica de Python. Comparar funciones mediante su AST normalizado y serializado equivale a comparar árboles sintácticos en lugar de cadenas de texto plano, replicando a escala de laboratorio el principio de herramientas industriales como SonarQube, PMD/CPD, MOSS o JPlag.

---

## Decisiones por componente

### 1. Extracción (`motor_ast/extractor.py`)

- `FuncionExtraida` es una dataclass inmutable conceptualmente que almacena nombre, ruta, línea y nodo AST original. No transforma el nodo; la normalización trabaja sobre copias independientes.
- `encontrar_archivos_python()` usa `Path.rglob("*.py")` y ordena por ruta relativa para determinismo.
- `parsear_archivo()` usa `tokenize.open()` para respetar declaraciones de codificación Python (UTF-8, Latin-1, BOM) y `ast.parse()` para analizar sin ejecutar código.
- Extrae `FunctionDef` y `AsyncFunctionDef`, incluyendo métodos de clase y funciones anidadas, ordenadas por número de línea.
- Manejo robusto de errores: los archivos con errores de sintaxis o lectura generan advertencias (`logger.warning`) y se omiten, permitiendo continuar con los archivos válidos restantes.

### 2. Normalización (`motor_ast/normalizador.py`)

- `normalizar_ast()` crea una copia profunda con `copy.deepcopy()` y aplica `NormalizadorAST` (heredera de `ast.NodeTransformer`). Deja el AST original intacto.
- **Identificadores:** el nombre raíz se sustituye por `FUNC`. Los parámetros y variables locales reciben `VAR1`, `VAR2`, etc., por orden de aparición, preservando la correspondencia dentro de la misma función.
- **Literales:** números y cadenas se reemplazan por el string `"LIT"` en nodos `Constant`. `True`, `False` y `None` se conservan.
- **Atributos y palabras clave:** `.metodo` y etiquetas de argumentos keyword se conservan sin renombrar para evitar asunciones semánticas inválidas.

### 3. Serialización (`motor_ast/serializador.py`)

- Recorrido recursivo pre-order: primero el nodo actual, luego sus hijos ordenados con `ast.iter_child_nodes()`.
- Genera tokens informativos: `Name:VARx`, `arg:VARx`, `Constant:LIT` (o booleanos/None). Los demás nodos emiten su clase sintáctica (`BinOp`, `Add`, `Return`, `If`, `For`, etc.).
- La función raíz emite `"FunctionDef"` o `"AsyncFunctionDef"`, asegurando que su nombre no altere la comparación.
- Es determinista y de solo lectura. No incluye delimitadores artificiales (`EndNode`) para no incorporar ruido a la extracción de n-gramas.

### 4. Métrica de Similitud (`motor_ast/similitud.py`)

- **Jaccard sobre n-gramas:** $J(A, B) = |A \cap B| / |A \cup B|$. Se evaluaron experimentalmente bigramas ($n=2$), trigramas ($n=3$) y cuatrigramas ($n=4$).
- **Selección de $n=3$:** ofrece la mejor separabilidad. Mantiene funciones con lógica distinta por debajo del 21% y clones/reordenamientos por encima del 80%.
- **Selección del umbral de $0.75$ ($75\%$):** provee una franja de seguridad amplia (más de 50 puntos porcentuales) entre positivos y negativos.
- Secuencias cortas ($len < n$) se representan como un único n-grama con todos sus tokens para no descartar funciones pequeñas.

### 5. Motor de búsqueda y CLI (`motor_ast/buscador.py` y `buscar_similares.py`)

- **Identificación de la función objetivo:** admite referencias con formato `archivo.py:nombre_funcion`. Utiliza `rpartition(":")` para no fallar ante rutas absolutas de Windows con letras de unidad (`C:\...`). Resuelve rutas relativas y absolutas con `pathlib.Path`. Si existen múltiples archivos con el mismo nombre o múltiples funciones con el mismo nombre en el mismo archivo, informa el error de ambigüedad con detalle de rutas/líneas.
- **Precomputación y eficiencia:** cada función del repositorio se normaliza y serializa **una sola vez**. Luego se compara la función objetivo contra las $N-1$ candidatas restantes.
- **Exclusión por identidad:** la función objetivo se excluye comparando `(archivo.resolve(), linea)`, asegurando que dos funciones con el mismo nombre en distintos archivos o líneas sí se comparen entre sí.
- **Ranking Top-K:** ordena por score descendente. Ante empates en el score, aplica un desempate determinista secundario: ruta de archivo ascendente, nombre de función ascendente y número de línea ascendente. Si hay menos candidatas que $K$, devuelve las disponibles sin inventar datos.
- **Aplicación del umbral:** clasifica a cada función con el booleano `es_duplicado`, pero no la elimina del ranking; esto permite al usuario inspeccionar las funciones más cercanas incluso si no superan el umbral.
- **Interfaz CLI (`buscar_similares.py`):** implementada con `argparse`. Maneja errores comunes del usuario (rutas inexistentes, funciones no encontradas) imprimiendo mensajes claros en `stderr` y saliendo con código 1 sin mostrar volcados de pila (*tracebacks*) innecesarios.

---

## Complejidad algorítmica

Para un repositorio con $M$ funciones de longitud promedio $L$ tokens:

1. **Extracción y análisis sintáctico:** $O(Archivos \cdot Tamaño)$.
2. **Normalización y serialización precomputada:** $O(M \cdot L)$.
3. **Generación de n-gramas y cálculo de Jaccard:** comparar la función objetivo con $M-1$ candidatas requiere $M-1$ intersecciones y uniones de conjuntos, cada una en $O(L)$. Total: $O(M \cdot L)$.
4. **Ordenamiento Top-K:** $O(M \log M)$.

**Complejidad global de una búsqueda:** $O(M \cdot L + M \log M)$.

En repositorios locales de tamaño mediano ($M \approx 500$ funciones), la búsqueda se completa en menos de un segundo en memoria, satisfaciendo ampliamente los requisitos de rendimiento del TP sin requerir indexación persistente ni bases de datos.

---

## Limitaciones conocidas

1. **Granularidad a nivel función:** Compara funciones individuales; no detecta clases duplicadas ni similitudes distribuidas entre múltiples funciones o módulos.
2. **Reordenamiento masivo de instrucciones:** Intercambiar bloques grandes de código quiebra los n-gramas en las fronteras de los bloques, lo que puede reducir el score de Jaccard por debajo del 75%.
3. **No detecta clones semánticos (Tipo 4):** Dos funciones que implementan algoritmos radicalmente distintos para resolver el mismo problema (ej. ordenamiento burbuja vs quicksort, o bucle iterativo vs recursión) poseen árboles AST diferentes y obtendrán baja similitud.
4. **Similitud estructural $\neq$ Equivalencia semántica:** Dos funciones pueden compartir una estructura sintáctica idéntica realizando tareas distintas en el dominio del negocio; la herramienta señala *candidatas a duplicado*, requiriendo validación humana.
