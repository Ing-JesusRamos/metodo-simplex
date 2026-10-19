GLOSSARY: dict[str, dict[str, str]] = {
    "Función objetivo": {
        "tecnico": "Expresión lineal Z = c1·x1 + c2·x2 + ... que se desea maximizar o minimizar.",
        "sencillo": "La fórmula que indica qué queremos conseguir. Por ejemplo, 'ganancia = 3·x1 + 2·x2'.",
    },
    "Restricción": {
        "tecnico": "Desigualdad o igualdad lineal a1·x1 + ... ≤ b que limita los valores admisibles.",
        "sencillo": "Un límite del problema. Por ejemplo, 'no podemos usar más de 4 horas de máquina'.",
    },
    "Variable de decisión": {
        "tecnico": "Variable xj cuyo valor se determina al resolver; sujeta a xj ≥ 0.",
        "sencillo": "Lo que decidimos: cuántas unidades producir de cada producto, por ejemplo.",
    },
    "Variable de holgura": {
        "tecnico": "Variable sj agregada a una restricción ≤ para convertirla en igualdad (coeficiente +1, costo 0). Mide la holgura o 'sobra' del lado izquierdo.",
        "sencillo": "Lo que sobra de un límite. Si usamos 3 de las 4 horas disponibles, la holgura es 1.",
    },
    "Variable de superávit": {
        "tecnico": "Variable ej agregada a una restricción ≥ (coeficiente −1, costo 0) para convertirla en igualdad.",
        "sencillo": "Cuánto pasamos de un mínimo requerido. Si exigimos al menos 5 y tenemos 7, el superávit es 2.",
    },
    "Variable artificial": {
        "tecnico": "Variable aj con costo Big-M en el objetivo, agregada a restricciones ≥ o = para obtener base inicial. Debe quedar fuera de la base en la solución óptima.",
        "sencillo": "Una variable 'de relleno' que usamos solo para poder empezar a calcular y que debe desaparecer en la solución final.",
    },
    "Big-M": {
        "tecnico": "Costo M→∞ asignado a las variables artificiales para expulsarlas de la base al optimizar.",
        "sencillo": "Un número muy grande que hace que las variables artificiales sean tan caras que el método las elimina solas.",
    },
    "Tableau": {
        "tecnico": "Tabla de coeficientes del sistema en forma de igualdad + fila de costos reducidos.",
        "sencillo": "La hoja de cálculo del método: cada fila es una ecuación y cada columna una variable.",
    },
    "Costo reducido (cj − zj)": {
        "tecnico": "Cuánto aumentaría (en max) la función objetivo por cada unidad que entra de la variable no básica xj.",
        "sencillo": "El 'precio de mejora': si es positivo en maximización, esa variable conviene incluirla.",
    },
    "Test del cociente (ratio test)": {
        "tecnico": "Para la columna entrante j: mínimo de b_i/a_ij sobre filas con a_ij > 0. Determina la fila pivote y garantiza factibilidad.",
        "sencillo": "El cálculo que decide cuál variable sale: cuántas unidades permite cada restricción antes de agotarse.",
    },
    "Pivote": {
        "tecnico": "Elemento en la intersección de la fila y columna elegidas; se normaliza a 1 y se usa para eliminar su columna (Gauss-Jordan).",
        "sencillo": "El punto de anclaje que cambia la tabla: muestra el intercambio de variables (entra X, sale Y).",
    },
    "Base": {
        "tecnico": "Conjunto de m variables asociadas una a una con las filas; en cada tableau la base tiene columnas unitarias.",
        "sencillo": "Las variables 'activas' de la solución actual: las que tienen un valor distinto de cero.",
    },
    "Región factible": {
        "tecnico": "Conjunto de puntos que cumplen todas las restricciones, incluida x ≥ 0.",
        "sencillo": "El área (o región) donde todas las condiciones se cumplen a la vez.",
    },
    "Vértice / punto extremo": {
        "tecnico": "Punto extremo del poliedro factible; el óptimo lineal siempre se alcanza en uno.",
        "sencillo": "Una esquina de la región factible. El método simplex va de esquina en esquina buscando la mejor.",
    },
    "Solución óptima": {
        "tecnico": "Punto factible donde la función objetivo alcanza su mejor valor (mínimo o máximo), dado por tabla con costos reducidos sin mejora.",
        "sencillo": "El mejor punto que cumple todas las condiciones: la respuesta del problema.",
    },
    "Soluciones óptimas alternativas": {
        "tecnico": "Cuando algún costo reducido de variable no básica es 0 en el óptimo, hay más de un óptimo (una arista completa).",
        "sencillo": "Hay más de una respuesta igual de buena: cualquier punto de la arista da el mismo valor óptimo.",
    },
    "Problema no acotado": {
        "tecnico": "Existe una variable entrante sin ninguna a_ij > 0, por lo que su valor puede crecer sin límite y Z también.",
        "sencillo": "El mejor valor no existe: se puede mejorar la solución infinitamente (algo falla en la formulación).",
    },
    "Problema infactible": {
        "tecnico": "Queda una variable artificial en la base con valor > 0 al alcanzar el estado óptimo.",
        "sencillo": "No hay ningún punto que cumpla todas las restricciones: son imposibles de satisfacer a la vez.",
    },
    "Gradiente": {
        "tecnico": "Vector ∇Z = (c1, c2, ...) perpendicular a las curvas de nivel, que indica la dirección de máximo crecimiento de Z.",
        "sencillo": "La 'flecha' que muestra hacia dónde crece más rápido tu objetivo en la gráfica.",
    },
}


def lookup(term: str, level: str = "tecnico") -> str | None:
    entry = GLOSSARY.get(term)
    if entry is None:
        return None
    return entry.get(level) or entry["tecnico"]


def search_terms(text: str) -> list[str]:
    return [term for term in GLOSSARY if term.lower() in text.lower()]