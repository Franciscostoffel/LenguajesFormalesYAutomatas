# Decisiones de diseño — etapa 2

## Arquitectura propuesta

Se separan las responsabilidades en módulos pequeños del paquete `motor_ast`.
La CLI quedará en la raíz y delegará el trabajo al paquete. Esta división facilita
comprender, probar y explicar cada transformación durante la defensa del trabajo.
El extractor ya está implementado; los demás módulos documentan sus
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
  No se copia ni transforma el nodo; la decisión de copiarlo para normalización
  queda pendiente de esa etapa.
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

## Decisiones pendientes

- **Métrica:** evaluar Jaccard sobre n-gramas y Levenshtein normalizada; justificar
  la elección. Si se elige Jaccard, definir el tamaño de los n-gramas.
- **Normalización:** definir el orden de asignación de `VAR1`, `VAR2`, etc., el
  tratamiento de ámbitos, funciones anidadas, atributos, nombres externos y
  docstrings. Se requiere mantener la correspondencia de variables, sustituir
  números y cadenas por `LIT` y evitar la influencia del nombre de la función.
- **Umbral:** elegir un valor configurable con evidencia de casos positivos y
  negativos; no hay un valor establecido.
- **Representación:** definir si copiar el AST antes de transformarlo y el formato
  exacto de tokens y límites estructurales; los metadatos ya se conservan mediante
  `FuncionExtraida`.
- **CLI y alcance futuro:** definir resolución de nombres ambiguos y evaluar si
  se requieren exclusiones configurables de directorios.
- **Validación posterior:** incorporar casos de renombrado, reordenamiento de
  líneas y funciones diferentes, y evaluar cómo responde la métrica elegida.

Estas decisiones se resolverán en etapas posteriores; solo la extracción está
implementada en esta entrega.
