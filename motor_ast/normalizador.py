"""Normaliza copias de funciones para comparar su estructura sintáctica.

Usa un diccionario por función analizada, sin resolver los alcances de Python.
El resultado es una representación para análisis, no para ejecutar.

Uso principal: normalizar_ast(funcion_extraida.nodo_ast).
El flujo es: copiar el subárbol -> transformar nombres y literales -> devolver
la copia. Los tipos de nodos y operadores se conservan: sumar y multiplicar
siguen siendo estructuras diferentes aunque sus variables cambien de nombre.

Para ver una demostración desde la raíz del proyecto:
    python -m motor_ast.normalizador
"""

import ast
from copy import deepcopy


class NormalizadorAST(ast.NodeTransformer):
    """Transforma una copia; crear una instancia por función raíz.

    Los nombres simples, incluidos externos y builtins, comparten el diccionario.
    Se conservan atributos y etiquetas de argumentos por palabra clave.

    NodeTransformer selecciona automáticamente visit_<tipo de nodo> al llamar
    a visit(). Por ejemplo, un Name se procesa en visit_Name(). Si no definimos
    un método para un tipo, se recorren sus hijos mediante generic_visit().
    En los métodos que sí definimos, continuamos la visita explícitamente cuando
    hace falta y devolvemos el nodo para conservarlo dentro del árbol.

    Esta clase modifica los nodos que recibe. La función pública normalizar_ast()
    se encarga de proporcionarle una copia independiente.

    Limitación: las funciones anidadas comparten el mapa de la raíz. Dos nombres
    escritos igual se consideran el mismo identificador aunque pertenezcan a
    ámbitos diferentes. No se resuelven imports, global/nonlocal ni los nombres
    guardados en campos especiales como los de except o match.
    """

    def __init__(self, raiz: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        """Recuerda la raíz para distinguirla de sus funciones anidadas."""
        self.raiz = raiz
        # Ejemplo: {"precio": "VAR1", "cantidad": "VAR2", "subtotal": "VAR3"}.
        # El diccionario pertenece a esta instancia; no se comparte entre llamadas.
        self.identificadores: dict[str, str] = {}

    def _normalizar_nombre(self, nombre: str) -> str:
        """Asigna un identificador nuevo o reutiliza el ya asociado al nombre."""
        if nombre not in self.identificadores:
            # La primera aparición fija el número; las siguientes lo conservan.
            self.identificadores[nombre] = f"VAR{len(self.identificadores) + 1}"
        return self.identificadores[nombre]

    def visit_FunctionDef(
        self, nodo: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> ast.FunctionDef | ast.AsyncFunctionDef:
        """Fija el nombre raíz y registra los parámetros antes de visitar el cuerpo."""
        # 'is' comprueba si es exactamente el objeto raíz, no si tiene igual nombre.
        if nodo is self.raiz:
            nodo.name = "FUNC"
        else:
            # El nombre anidado usa el mismo mapa que sus referencias en Name.
            nodo.name = self._normalizar_nombre(nodo.name)

        argumentos = nodo.args
        # Registramos todos los parámetros antes de visitar anotaciones y valores
        # por defecto: en f(a: int, b), a y b deben recibir VAR1 y VAR2 antes de int.
        # Orden: exclusivos por posición (/), normales, *args, exclusivos por
        # palabra clave y **kwargs. Aquí se llena el mapa; visit_arg renombra luego.
        parametros = [*argumentos.posonlyargs, *argumentos.args]
        if argumentos.vararg is not None:
            parametros.append(argumentos.vararg)
        parametros.extend(argumentos.kwonlyargs)
        if argumentos.kwarg is not None:
            parametros.append(argumentos.kwarg)
        for parametro in parametros:
            self._normalizar_nombre(parametro.arg)

        # Visita parámetros, cuerpo, decoradores y anotación de retorno. Si se
        # omitiera, las variables y los literales de esos hijos quedarían intactos.
        self.generic_visit(nodo)
        return nodo

    def visit_AsyncFunctionDef(self, nodo: ast.AsyncFunctionDef) -> ast.AsyncFunctionDef:
        """Aplica las mismas reglas a una función asíncrona."""
        self.visit_FunctionDef(nodo)
        return nodo

    def visit_arg(self, nodo: ast.arg) -> ast.arg:
        """Renombra la declaración de un parámetro y visita su posible anotación."""
        nodo.arg = self._normalizar_nombre(nodo.arg)
        self.generic_visit(nodo)
        return nodo

    def visit_Name(self, nodo: ast.Name) -> ast.Name:
        """Renombra un nombre simple, tanto al leerlo como al asignarle un valor."""
        # Se cambia id pero se conserva ctx (Load, Store o Del).
        # En obj.metodo(), obj es un Name; 'metodo' está en Attribute.attr y no
        # se modifica. Tampoco se cambia keyword.arg, la etiqueta de f(limite=3).
        nodo.id = self._normalizar_nombre(nodo.id)
        return nodo

    def visit_Constant(self, nodo: ast.Constant) -> ast.Constant:
        """Sustituye números y cadenas, manteniendo el nodo Constant existente."""
        # bool es subclase de int, pero True y False se conservan explícitamente.
        # También se conservan None, bytes y Ellipsis. Los docstrings, en cambio,
        # son cadenas y pasan a LIT sin eliminar su nodo del cuerpo de la función.
        if isinstance(nodo.value, (int, float, complex, str)) and not isinstance(nodo.value, bool):
            # Se usa una cadena válida como valor de Constant, no un nodo inventado.
            # Esto pierde el tipo/valor original del literal: no es código a ejecutar.
            nodo.value = "LIT"
            # Ignora detalles de escritura como el prefijo u de u'texto'.
            nodo.kind = None
        return nodo


def normalizar_ast(
    nodo: ast.FunctionDef | ast.AsyncFunctionDef,
) -> ast.FunctionDef | ast.AsyncFunctionDef:
    """Devuelve una copia normalizada de una función y deja intacto su AST original.

    Conserva las ubicaciones de origen. Para comparar estructura con ast.dump(),
    usar include_attributes=False. Solo acepta definiciones de función.

    Cada llamada crea un mapa nuevo y reinicia la numeración de variables.
    Lanza TypeError si se recibe otro tipo de nodo, como un Module completo.
    """
    if not isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef)):
        raise TypeError("Se esperaba un nodo FunctionDef o AsyncFunctionDef")
    # Una copia superficial compartiría los nodos hijos con el árbol original.
    copia = deepcopy(nodo)
    # visit() inicia el despacho a los métodos visit_*. Estos modifican la copia
    # en el lugar y devuelven los mismos nodos, por eso podemos devolver 'copia'.
    NormalizadorAST(copia).visit(copia)
    return copia


def _demostrar_normalizacion() -> None:
    """Extrae ejemplos reales y muestra el antes y el después sin ejecutarlos.

    unparse() reconstruye texto legible; dump() muestra la estructura de nodos.
    Son herramientas de visualización: el resultado principal sigue siendo el AST.
    """
    from pathlib import Path

    from motor_ast.extractor import extraer_funciones_directorio

    directorio = Path(__file__).resolve().parent.parent / "ejemplos"
    for funcion in extraer_funciones_directorio(directorio):
        normalizado = normalizar_ast(funcion.nodo_ast)
        print(f"\nArchivo: {funcion.archivo.name}, función: {funcion.nombre}")
        print("\nCódigo original:")
        print(ast.unparse(funcion.nodo_ast))
        print("\nRepresentación normalizada (solo para análisis):")
        print(ast.unparse(normalizado))
        print("\nAST normalizado:")
        print(ast.dump(normalizado, indent=4, include_attributes=False))


if __name__ == "__main__":
    # Se ejecuta con -m motor_ast.normalizador; importar el módulo no lanza la demo.
    _demostrar_normalizacion()
