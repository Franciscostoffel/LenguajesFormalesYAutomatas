# Decisiones de diseño — etapa 1

## Arquitectura propuesta

Se separan las responsabilidades en módulos pequeños del paquete `motor_ast`.
La CLI quedará en la raíz y delegará el trabajo al paquete. Esta división facilita
comprender, probar y explicar cada transformación durante la defensa del trabajo.
Por ahora, los módulos solo documentan sus responsabilidades futuras.

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
- Verificar inicialmente solo la importación de módulos; aún no hay algoritmos
  cuyo comportamiento se pueda probar.

## Decisiones pendientes

- **Métrica:** evaluar Jaccard sobre n-gramas y Levenshtein normalizada; justificar
  la elección. Si se elige Jaccard, definir el tamaño de los n-gramas.
- **Normalización:** definir el orden de asignación de `VAR1`, `VAR2`, etc., el
  tratamiento de ámbitos, funciones anidadas, atributos, nombres externos y
  docstrings. Se requiere mantener la correspondencia de variables, sustituir
  números y cadenas por `LIT` y evitar la influencia del nombre de la función.
- **Umbral:** elegir un valor configurable con evidencia de casos positivos y
  negativos; no hay un valor establecido.
- **Representación:** definir cómo conservar los metadatos, si copiar el AST antes
  de transformarlo y el formato exacto de tokens y límites estructurales.
- **Extracción y CLI:** definir soporte de funciones asíncronas, resolución de
  nombres ambiguos, tratamiento de archivos inválidos y directorios excluidos.
- **Validación posterior:** incorporar casos de renombrado, reordenamiento de
  líneas y funciones diferentes, y evaluar cómo responde la métrica elegida.

Estas decisiones se resolverán en etapas posteriores; no hay algoritmos ni
interfaz CLI implementados en esta entrega.
