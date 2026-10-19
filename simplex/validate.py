from .problem import Constraint, LPProblem


def parse_float(text: str, label: str) -> float:
    """Convierte texto en número flotante o lanza un error explicable al usuario."""
    cleaned = text.strip().replace(",", ".")
    if not cleaned:
        raise ValueError(f"El campo '{label}' no puede estar vacío.")
    try:
        value = float(cleaned)
    except ValueError:
        raise ValueError(f"'{text}' no es un número válido en el campo '{label}'.")
    if value != value or abs(value) > 1e15:
        raise ValueError(f"El valor de '{label}' es demasiado grande para procesarlo.")
    return value


def flip_constraint_to_positive_rhs(constraint: Constraint) -> Constraint:
    def flipped_relation(relation: str) -> str:
        return {">=": "<=", "<=": ">="}.get(relation, relation)

    flipped_coefficients = tuple(-value for value in constraint.coefficients)
    return Constraint(flipped_coefficients, flipped_relation(constraint.relation), -constraint.rhs)


def normalize_problem(problem: LPProblem) -> LPProblem:
    """Mantiene todos los rhs >= 0 (multiplica restricciones negativas por -1)."""
    normalized_constraints = []
    for constraint in problem.constraints:
        if constraint.rhs < 0:
            normalized_constraints.append(flip_constraint_to_positive_rhs(constraint))
        else:
            normalized_constraints.append(constraint)
    return LPProblem(problem.objective_sense, problem.objective_coeffs, tuple(normalized_constraints))


def build_problem(
    sense: str,
    objective_coeffs: list[float],
    constraints_coeffs: list[list[float]],
    relations: list[str],
    right_hand_sides: list[float],
) -> LPProblem:
    """Arma y valida un problema desde listas de números ya parseados."""
    problem = LPProblem(
        objective_sense=sense.strip().lower(),
        objective_coeffs=tuple(objective_coeffs),
        constraints=tuple(
            Constraint(tuple(row), relation, rhs)
            for row, relation, rhs in zip(constraints_coeffs, relations, right_hand_sides)
        ),
    )
    problem.validate()
    return normalize_problem(problem)


EXAMPLE_PROBLEM = LPProblem(
    objective_sense="max",
    objective_coeffs=(3.0, 2.0),
    constraints=(
        Constraint((1.0, 1.0), "<=", 4.0),
        Constraint((2.0, 1.0), "<=", 5.0),
    ),
)