# Decisiones de diseño — etapa 3

## Arquitectura propuesta

Se separan las responsabilidades en módulos pequeños del paquete `motor_ast`.
La CLI quedará en la raíz y delegará el trabajo al paquete. Esta división facilita
comprender, probar y explicar cada transformación durante la defensa del trabajo.
El extractor y el normalizador están implementados; los demás módulos documentan sus
responsabilidades futuras.

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

### Relación con la teoría y validación

Normalizar es transformar representaciones sintácticas hacia una forma común.
Dos textos que difieren en identificadores o valores pueden conservar los mismos
patrones de nodos y producir árboles normalizados equivalentes. Se pierde la
información concreta de esos nombres y literales, pero se conservan `BinOp`,
`If`, `Return` y otros nodos que describen la estructura a comparar.

Recorrer significa visitar nodos; transformar añade cambios en nodos o campos.
Esto se relaciona con traducción dirigida por la sintaxis: las reglas se aplican
según el tipo de nodo del árbol generado por el análisis sintáctico de Python.
La normalización no demuestra que dos funciones hagan lo mismo.

Las pruebas comparan `ast.dump()` y verifican equivalencias, diferencias entre
operadores, independencia del original, determinismo, integración con extracción
y la política de identificadores. `python -m motor_ast.normalizador` muestra los
ejemplos reales sin implementar serialización ni búsqueda.

## Decisiones pendientes

- **Métrica:** evaluar Jaccard sobre n-gramas y Levenshtein normalizada; justificar
  la elección. Si se elige Jaccard, definir el tamaño de los n-gramas.
- **Umbral:** elegir un valor configurable con evidencia de casos positivos y
  negativos; no hay un valor establecido.
- **Representación:** definir el formato exacto de tokens y límites estructurales;
  los metadatos ya se conservan mediante `FuncionExtraida` y el AST se copia antes
  de normalizar.
- **CLI y alcance futuro:** definir resolución de nombres ambiguos y evaluar si
  se requieren exclusiones configurables de directorios.
- **Validación posterior:** incorporar casos de renombrado, reordenamiento de
  líneas y funciones diferentes, y evaluar cómo responde la métrica elegida.

Estas decisiones se resolverán en etapas posteriores; la extracción y la
normalización están implementadas en esta entrega.
