"""Cómo leer cada gráfica: textos breves en lenguaje claro y técnico."""


def feasible_region_2d(level: str = "basico") -> str:
    if level == "basico":
        return (
            "Cada línea es una restricción (una frontera). La zona sombreada es la región factible: "
            "ahí todas las condiciones se cumplen. El punto rojo es el vértice donde se alcanza la "
            "solución óptima. Las líneas punteadas son curvas de nivel de Z; la flecha muestra hacia "
            "dónde crece el objetivo."
        )
    if level == "intermedio":
        return (
            "El sombreado se obtiene evaluando las restricciones (incluida x ≥ 0) en una cuadrícula. "
            "Las líneas de nivel Z = c·x son rectas perpendiculares al gradiente. En maximización "
            "movemos la recta en dirección del gradiente hasta que toca el último vértice factible; "
            "ese vértice es el óptimo."
        )
    return (
        "Se discretiza el cuadrante x ≥ 0 y se conservan los puntos que cumplen a·x (≤/≥/=) b. "
        "El conjunto es convexo; el gradiente ∇Z es la dirección de máximo crecimiento. En el "
        "óptimo, el hiperplano de nivel Z* es soporte de la región factible (los vértices marcados "
        "son intersecciones de pares de fronteras activas)."
    )


def objective_progress(level: str = "basico") -> str:
    if level == "basico":
        return (
            "Esta línea muestra cómo cambia el valor de Z en cada iteración del método. En "
            "maximización nunca baja: cada paso mejora (o iguala) la solución, hasta que se "
            "estabiliza en el óptimo."
        )
    if level == "intermedio":
        return (
            "El valor de la fila objetivo (columna derecha del tableau) al inicio de cada iteración. "
            "Es monótono por el criterio de selección: entran variables con costo reducido positivo, "
            "por lo que Z no puede empeorar en maximización."
        )
    return (
        "Secuencia de valores de la columna del lado derecho de la fila objetivo. La monotonía "
        "refleja la regla de entrada (max): si cj − zj > 0, el paso incrementa Z; en degeneración "
        "puede mantenerse igual."
    )


def feasible_region_3d(level: str = "basico") -> str:
    if level == "basico":
        return (
            "Cada plano es una restricción. Los puntos azules forman la región factible en tres "
            "dimensiones. El punto rojo es el vértice óptimo y la flecha indica la dirección de "
            "crecimiento del objetivo. Puedes rotar la figura con el ratón."
        )
    if level == "intermedio":
        return (
            "La nube de puntos es una muestra de la región factible (cuadrícula 3D filtrada por las "
            "restricciones). El óptimo es un punto extremo del poliedro; el gradiente ∇Z se dibuja "
            "desde el óptimo para visualizar por qué es el último plano de nivel que toca la región."
        )
    return (
        "Región factible = intersección de semiespacios a·x ≤ b y cuadrante x ≥ 0. Se aproxima por "
        "muestreo uniforme. El vértice óptimo coincide con la proyección del gradiente sobre el "
        "poliedro (condiciones KKT)."
    )


def alternate_optima_note() -> str:
    return (
        "Existen soluciones óptimas alternativas: hay otra esquina (o toda una arista) con el mismo "
        "valor de Z. En la gráfica verás que la línea de nivel del óptimo coincide con una frontera."
    )