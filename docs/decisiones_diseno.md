# Decisiones de diseño — etapa 4

## Arquitectura propuesta

Se separan las responsabilidades en módulos pequeños del paquete `motor_ast`.
La CLI quedará en la raíz y delegará el trabajo al paquete. Esta división facilita
comprender, probar y explicar cada transformación durante la defensa del trabajo.
El extractor, el normalizador y el serializador están implementados; los demás
módulos documentan sus responsabilidades futuras.

| Archivo | Responsabilidad prevista |
| --- | --- |
| `buscar_similares.py` | Leer argumentos de terminal y presentar resultados. |
| `motor_ast/extractor.py` | Recorrer archivos `.py`, parsearlos con `ast.parse()` y registrar funciones, nombre, archivo, línea y subárbol. |
| `motor_ast/normalizador.py` | Reemplazar identificadores y literales, preservando referencias y estructura. |
| `motor_ast/serializador.py` | Recorrer el AST normalizado en pre-order y producir tokens deterministas. |
| `motor_ast/similitud.py` | Calcular la similitud entre secuencias de tokens. |
| `motor_ast/buscador.py` | Coordinar comparaciones y ordenar las K mejores coincidencias. |

## Flujo de datos previsto y fundamento teórico

1. Un directorio aportará archivos Python al extractor.
2. El análisis sintáctico de Python producirá AST, de los que se obtendrán
   funciones y metadatos de origen.
3. La normalización transformará cada subárbol para reducir diferencias
   irrelevantes de nombres y literales.
4. El recorrido pre-order traducirá cada árbol normalizado a una secuencia.
5. La métrica comparará las secuencias y el buscador ordenará los resultados.
6. La CLI mostrará puntuaciones y ubicaciones de las funciones.

El AST es una abstracción de la estructura sintáctica derivada de la gramática de
Python. La normalización y la serialización se relacionan con transformaciones
de representaciones sintácticas y traducción dirigida por la sintaxis. No se
implementarán un analizador léxico ni un parser propios. Los tokens generados
desde el AST no deben confundirse con los tokens del análisis léxico.

## Decisiones iniciales

- Usar la biblioteca estándar `ast` para el procesamiento sintáctico.
- Proponer Python 3.10 o superior como base del entorno.
- Usar pytest para pruebas incrementales y evitar dependencias innecesarias.
- Conservar el `.gitignore` existente, que ya contempla Python, entornos y pytest.
- Mantener la prueba inicial de importación y añadir pruebas reales del extractor
  con archivos temporales.

## Extracción implementada

- `FuncionExtraida` es una dataclass con nombre, ruta, línea y nodo AST original.
  La extracción no copia ni transforma el nodo; el normalizador trabaja sobre una
  copia independiente.
- `encontrar_archivos_python()` usa `Path.rglob()` y ordena por ruta relativa para
  obtener un procesamiento determinista. Valida que la ruta exista y sea carpeta.
- `parsear_archivo()` usa `tokenize.open()` para respetar UTF-8, BOM o una
  declaración de codificación Python, y `ast.parse()` para analizar sin ejecutar.
- `extraer_funciones()` usa `ast.walk()` y filtra `FunctionDef` y
  `AsyncFunctionDef`. Esto incluye métodos y funciones anidadas sin comparar
  clases completas. Ordena los resultados por línea: `ast.walk()` por sí solo
  no garantiza el orden textual de las funciones.
- `extraer_funciones_directorio()` coordina las tres operaciones anteriores.
- Los errores del directorio de entrada se propagan al llamador. Al procesar cada
  archivo, los errores de lectura, codificación y sintaxis generan una advertencia
  mediante `logging`, con ruta y detalle; se omite ese archivo y se continúa.
  Así un archivo inválido no impide analizar los restantes y la omisión es visible.
  El resultado puede ser parcial o vacío si no se extrae ninguna función.
  `parsear_archivo()` mantiene la propagación de errores al usarse individualmente.
- No se aplican exclusiones de carpetas. El directorio de entrada debe elegirse
  teniendo en cuenta que también se analizarán sus subcarpetas.
- `python -m motor_ast.extractor` ejecuta una demostración sobre `ejemplos/`.
  La CLI definitiva se mantiene pendiente.

## Normalización implementada

### Transformación y conservación del original

`normalizar_ast()` acepta un `FunctionDef` o `AsyncFunctionDef`, crea una copia
profunda con `copy.deepcopy()` y aplica una instancia nueva de `NormalizadorAST`.
La clase hereda de `ast.NodeTransformer`: sus métodos `visit_*` transforman los
nodos seleccionados y `generic_visit()` continúa por sus hijos. No se modifican
los archivos, el nodo extraído ni sus metadatos originales.

Se conservan los tipos de nodos, operadores, contextos `Load`/`Store`, ubicación
y orden de las instrucciones. Al comparar con `ast.dump()` se omiten los atributos
de ubicación usando `include_attributes=False`: los números de línea no deben
influir en la equivalencia estructural.

### Identificadores y política de alcances

- El nombre de la función raíz se sustituye por `FUNC`.
- Un diccionario asigna `VAR1`, `VAR2`, etc., por primera aparición de cada nombre
  original. Se reinicia para cada llamada pública a `normalizar_ast()`.
- Antes de visitar cada definición, se registran sus parámetros: posicionales
  exclusivos, normales, `*args`, exclusivos por palabra clave y `**kwargs`. Así las
  anotaciones y valores por defecto no desplazan la numeración de los parámetros.
- Se transforman los campos `Name.id` y `arg.arg`. Los nombres simples externos,
  builtins, nombres de funciones llamadas y nombres en anotaciones usan la misma
  regla; no se resuelven sus definiciones. Esto puede equiparar llamadas distintas
  como `len(datos)` y `medir(datos)`; la similitud no prueba equivalencia semántica.
- Las funciones anidadas forman parte del subárbol de la raíz. Sus nombres se
  asignan mediante el mismo diccionario para coincidir con referencias `Name`;
  sus parámetros y cuerpos también comparten ese mapa. Al extraer una función
  anidada y normalizarla por separado, pasa a ser otra raíz y empieza desde cero.
- No se distinguen ámbitos: dos nombres escritos igual se tratan como el mismo,
  incluso si uno sombrea al otro en una función anidada, lambda o comprensión.
  No se intenta resolver closures, recursión o referencias globales por semántica.
- Se conservan `Attribute.attr` y `keyword.arg`: `.metodo` y las etiquetas de
  llamadas por palabra clave no se renombran. Renombrar un parámetro no garantiza
  que una llamada por palabra clave dentro de la misma función quede enlazada.
- Los nombres guardados en otros campos, como declaraciones `global`/`nonlocal`,
  imports y alias, variables de `except`, patrones `match` o nombres de clases y
  parámetros de tipo, no tienen reglas especiales en esta etapa. Pueden conservar
  nombres originales e impedir equivalencias bajo renombrado en esos casos.

Esta política prioriza una transformación pequeña y explicable sobre un análisis
semántico completo. El árbol normalizado no debe compilarse ni ejecutarse.

### Literales

Los valores `int`, `float`, `complex` y `str` pasan a ser la cadena `"LIT"` dentro
del mismo nodo `Constant`; su atributo `kind` se limpia para ignorar prefijos como
`u`. No se introduce un tipo de nodo inventado. `True`, `False`, `None`, bytes y
`Ellipsis` se conservan; se excluye `bool` explícitamente porque hereda de `int`.
Los signos negativos siguen siendo nodos `UnaryOp`, y se mantienen los nodos de
las f-strings aunque cambien sus segmentos de texto. Los docstrings se normalizan
como cadenas, sin borrar su nodo: tener docstring sigue siendo una diferencia
estructural frente a no tenerlo.

No se preserva la semántica ejecutable ni el tipo de los números normalizados.
`ast.unparse()` se usa solo para visualizar; el resultado principal es el AST.
No se afirma que todas las construcciones avanzadas puedan regenerarse o
compilarse tras sustituir sus constantes. La transformación está orientada a
funciones con los nodos habituales de asignación, operaciones, control y llamadas.

## Serialización implementada

### Recorrido pre-order y algoritmo

La función `serializar_ast()` recibe un nodo AST (típicamente una función normalizada)
y genera una lista plana de strings mediante un recorrido recursivo pre-order:

1. **Visita del nodo actual**: se genera el token representativo del nodo raíz del
   subárbol mediante `_token_de_nodo()`.
2. **Recorrido recursivo de los hijos**: se itera ordenadamente sobre los nodos hijos
   usando `ast.iter_child_nodes()`, que recorre los subnodos sintácticos de izquierda
   a derecha según el orden natural del AST.

No se utiliza `ast.walk()`, dado que dicho iterador no garantiza un orden topológico
ni pre-order determinista entre hermanos y niveles del árbol.

### Representación de tokens

Se adopta una representación consistente y legible:

- **Nodos con valores normalizados relevantes**:
  - `Name`: se emite `Name:<id>` (por ejemplo `Name:VAR1`, `Name:VAR2`).
  - `arg`: se emite `arg:<nombre>` (por ejemplo `arg:VAR1`).
  - `Constant`: se emite `Constant:<valor>` (por ejemplo `Constant:LIT`, `Constant:True`, `Constant:None`).
- **Definiciones de función**:
  - Tanto `FunctionDef` como `AsyncFunctionDef` emiten únicamente el nombre de su tipo de
    nodo (`FunctionDef` o `AsyncFunctionDef`). De esta manera, el nombre original o el
    marcador `FUNC` no se introduce como token, cumpliendo la pauta de que el nombre de
    la función no influye en la comparación.
- **Demás nodos sintácticos**:
  - Se emite el nombre exacto de la clase del nodo (`type(nodo).__name__`), como `BinOp`,
    `Add`, `Sub`, `Mult`, `Return`, `If`, `For`, `While`, `Compare`, `Eq`, `Gt`, `Assign`,
    `Call`, `arguments`, `Load`, `Store`, `Attribute`, `keyword`, etc.

### Información conservada vs. información omitida

- **Se conserva**:
  - La jerarquía y orden secuencial de todas las instrucciones y expresiones.
  - La diferenciación de operadores (`Add` vs `Sub` vs `Mult`).
  - Las estructuras de control (`If` vs `For` vs `While`).
  - La correspondencia de variables normalizadas (`VAR1`, `VAR2`, etc.).
  - Las repeticiones y la frecuencia exacta de cada token (no se emplean conjuntos).
  - Los contextos de acceso sintáctico (`Load`, `Store`).
- **Se omite**:
  - Nombres originales de variables, parámetros y funciones.
  - Valores literales originales (números y cadenas de texto reemplazados por `LIT`).
  - Información de ubicación física en el código fuente (`lineno`, `col_offset`, rutas de archivos).
  - Cadenas textuales de atributos o etiquetas de argumentos por palabra clave no normalizados,
    evitando filtración de nombres originales al serializar.

### Determinismo e inmutabilidad

La serialización es estrictamente determinista: procesar el mismo árbol o dos árboles
estructuralmente equivalentes produce secuencias de tokens idénticas, con el mismo orden y
longitud. `serializar_ast()` es una operación de solo lectura; no modifica, reemplaza ni
agrega atributos al AST recibido.

### Limitaciones de la linealización lineal

Aplanar un árbol bidimensional a una secuencia lineal 1D mediante pre-order presenta
una limitación teórica conocida: en árboles de aridad variable sin marcadores de cierre
(como paréntesis o tokens `End`), ciertas estructuras diferentes podrían teóricamente
producir la misma secuencia. 

Sin embargo, para el AST de Python, la mayoría de los nodos poseen una aridad fija y roles
claramente delimitados (por ejemplo, `BinOp` contiene siempre operando izquierdo, operador y
operando derecho; `Return` contiene una expresión; etc.), y los bloques con múltiples
instrucciones son secuencias contenidas en listas de nodos (`body`). 
Se decidió no introducir tokens de cierre (`EndNode`) para mantener las secuencias limpias,
concisas y directamente preparadas para la posterior extracción de n-gramas sin ruido
artificial.

## Decisiones pendientes

- **Métrica:** evaluar Jaccard sobre n-gramas y Levenshtein normalizada; justificar
  la elección. Si se elige Jaccard, definir el tamaño de los n-gramas.
- **Umbral:** elegir un valor configurable con evidencia de casos positivos y
  negativos; no hay un valor establecido.
- **Buscador y CLI:** implementar ranking de las K mejores coincidencias y CLI con
  `argparse`.
- **Validación posterior:** incorporar casos de prueba de renombrado, reordenamiento
  de líneas y funciones diferentes, evaluando la respuesta de la métrica.

Estas decisiones se resolverán en etapas posteriores; la extracción, normalización y
serialización están implementadas en esta entrega.
