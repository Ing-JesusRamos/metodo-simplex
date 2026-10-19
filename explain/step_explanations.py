"""Explicaciones de cada paso del algoritmo, con tres niveles de detalle."""

from simplex.problem import LPProblem
from simplex.big_m import SimplexStep, SimplexResult

LEVELS = ("basico", "intermedio", "tecnico")


def _fmt(value: float) -> str:
    if abs(float(value) - round(float(value))) < 1e-9:
        return str(int(round(float(value))))
    return f"{float(value):.5g}"


def _column_index(step: SimplexStep, name: str | None) -> int | None:
    if name is None:
        return None
    try:
        return list(step.column_labels).index(name)
    except ValueError:
        return None


def _reduce_cost_of(step: SimplexStep, name: str) -> float | None:
    index = _column_index(step, name)
    if index is None:
        return None
    return float(step.reduced_costs[index])


def classify_optimality(step: SimplexStep) -> str:
    nonbasic_options = [
        (label, reduced_cost)
        for label, reduced_cost in zip(step.column_labels, step.reduced_costs)
        if label not in step.basis_names and label.startswith("x")
    ]
    if any(abs(reduced_cost) < 1e-6 for _, reduced_cost in nonbasic_options):
        return "alternativo"
    return "unico"


def explain_build(step: SimplexStep, problem: LPProblem, big_m: float) -> str:
    lines = []
    lines.append("PASO 0 — Convertir el problema a la forma que usa el método.")
    explanation = (
        "No podemos sumar variables de más ni de menos, así que primero transformamos "
        "cada restricción en una igualdad agregando variables auxiliares:\n"
    )
    for index, constraint in enumerate(problem.constraints, start=1):
        base = " + ".join(f"{_fmt(coef)}·{name}" for coef, name in zip(constraint.coefficients, step.column_labels[:problem.num_variables]))
        if constraint.relation == "<=":
            explanation += f"  • Semana {index}: {base} ≤ {_fmt(constraint.rhs)}  →  se suma una holgura s{index}.\n"
        elif constraint.relation == ">=":
            explanation += f"  • Restricción {index}: {base} ≥ {_fmt(constraint.rhs)}  →  se resta un superávit e{index} y se suma una artificial a{index}.\n"
        else:
            explanation += f"  • Restricción {index}: {base} = {_fmt(constraint.rhs)}  →  se suma una artificial a{index}.\n"
    explanation += (
        f"\nLas variables artificiales llevan costo Big-M = {_fmt(big_m)} en el objetivo "
        "(número muy grande) para que el método las saque de la base lo antes posible.\n"
    )
    lines.append(explanation)
    lines.append("La tabla inicial lista es la que ves a la izquierda. Ahora empieza el ciclo: elegir variable entrante.")
    return "\n".join(lines)


def explain_entering(step: SimplexStep) -> str:
    if step.entering is None:
        return ""
    reduced_cost = _reduce_cost_of(step, step.entering)
    lines = []
    lines.append(f"ELEGIR VARIABLE ENTRANTE — {step.entering}")
    if reduced_cost is not None and reduced_cost > 1e-9:
        lines.append(
            f"Miramos la fila de costos reducidos (cj − zj) y buscamos los valores positivos. "
            f"{step.entering} tiene {_fmt(reduced_cost)}: cada unidad que entra sube la función objetivo "
            f"en {_fmt(reduced_cost)}. Es el mejor candidato, así que {step.entering} entra a la base."
        )
    else:
        lines.append(
            f"{step.entering} tiene un costo reducido favorable y por eso entra a la base "
            "(es la variable que más mejora el objetivo en este paso)."
        )
    lines.append(
        "Concepto clave: mientras haya una variable no básica con costo reducido positivo "
        "(en maximización), el óptimo aún no se alcanzó."
    )
    return "\n".join(lines)


def explain_ratio_test(step: SimplexStep) -> str:
    if step.entering is None or step.leaving is None or len(step.ratios) == 0:
        return ""
    lines = []
    lines.append(f"TEST DEL COCIENTE — cuál sale: {step.leaving}")
    rows = []
    for row_index, (ratio, basis_name) in enumerate(zip(step.ratios, step.basis_names)):
        rhs_value = float(step.matrix[row_index, -1])
        coefficient = float(step.matrix[row_index, _column_index(step, step.entering)])
        if ratio is None:
            rows.append(f"  • {basis_name}: b/coef no aplica (coeficiente ≤ 0), puede crecer sin agotarse.")
        else:
            rows.append(f"  • {basis_name}: {_fmt(rhs_value)} / {_fmt(coefficient)} = {_fmt(ratio)}")
    lines.extend(rows)
    pivot_row = step.pivot_row
    if pivot_row is not None:
        chosen = step.basis_names[pivot_row]
        lines.append(
            f"Tomamos el cociente mínimo ({_fmt(min(r for r in step.ratios if r is not None))}). "
            f"La fila {chosen} es la que se agota primero: si metiéramos más de lo que permite, "
            f"violaríamos la restricción. Por eso {chosen} sale de la base."
        )
    return "\n".join(lines)


def explain_pivot(step: SimplexStep) -> str:
    if step.pivot_value is None or step.entering is None or step.leaving is None:
        return ""
    return (
        f"PIVOTE — intercambio\n"
        f"En la intersección de la fila {step.leaving} y la columna {step.entering} está el pivote "
        f"{_fmt(step.pivot_value)}. Dividimos esa fila entre el pivote y luego sumamos/restamos "
        f"múltiplos de ella a las demás filas (incluida la del objetivo) para que la columna de "
        f"{step.entering} quede con un 1 y el resto en 0. Eso nos lleva a la siguiente tabla."
    )


def explain_iteration(step: SimplexStep) -> str:
    sections = [
        f"Iteración — en la tabla actual, {step.entering} entra y {step.leaving} sale.",
        explain_entering(step),
        explain_ratio_test(step),
        explain_pivot(step),
    ]
    return "\n\n".join(section for section in sections if section)


def explain_final(step: SimplexStep, result: SimplexResult) -> str:
    if step.kind == "optimal":
        lines = ["ÓPTIMO ENCONTRADO"]
        original_names = [label for label in step.column_labels if label.startswith("x")]
        lines.append("Los valores de las variables son:\n" + "\n".join(
            f"  • {name} = {_fmt(step.solution.get(name, 0.0))}" for name in original_names
        ))
        lines.append(
            f"Todos los costos reducidos quedaron sin mejora posible, así que ninguna variable "
            f"fuera de la base puede mejorar Z. Resultado óptimo con Z = {_fmt(result.objective_value)}."
        )
        if classify_optimality(step) == "alternativo":
            lines.append(
                "Nota: hay óptimos alternativos (algún costo reducido es 0). Otra esquina de la "
                "región daría el mismo valor óptimo."
            )
        return "\n\n".join(lines)
    if step.kind == "infeasible":
        return (
            "INFACTIBLE\n"
            "El método terminó pero una variable artificial quedó en la base con valor > 0. "
            "Eso significa que las restricciones del problema son contradictorias: no existe "
            "ningún punto que las cumpla todas a la vez. Revisa los signos o los valores del "
            "lado derecho (b)."
        )
    return (
        "NO ACOTADO\n"
        "La variable entrante no tiene ninguna restricción que la limite (no hay coeficientes "
        f"positivos en su columna), así que puede crecer sin tope y Z también. "
        "Suelen faltar restricciones: revisa si el problema está bien planteado."
    )


def explain_step(step: SimplexStep, problem: LPProblem, result: SimplexResult, level: str = "basico") -> str:
    if step.kind == "build":
        return explain_build(step, problem, result.big_m)
    if step.kind == "iterate":
        return explain_iteration(step)
    return explain_final(step, result)


def interpret_solution(result: SimplexResult) -> str:
    original_names = list(result.solution.keys())
    if result.status == "optimal":
        values = ",\n".join(f"  {name} = {_fmt(value)}" for name, value in result.solution.items())
        action = "maximizamos" if result.sense == "max" else "minimizamos"
        return (
            f"Solución encontrada para {action} Z:\n{values}\n\n"
            f"Valor óptimo de Z = {_fmt(result.objective_value)}.\n\n"
            "Resumen: para alcanzar este resultado, la solución usa exactamente las unidades "
            "que muestran las variables. Si alguna era una holgura o superávit, su valor indica "
            "cuánto sobra o cuánto supera cada límite."
        )
    if result.status == "infeasible":
        return (
            "Las restricciones son contradictorias: no existe solución. "
            "Revisa los signos de ≥/≤ y los valores del lado derecho."
        )
    return (
        "El problema es no acotado: no hay mejor valor finito. "
        "Suele faltar alguna restricción que limite el problema."
    )