import numpy as np
from dataclasses import dataclass, field

from .problem import LPProblem
from .validate import normalize_problem

NEGLIGIBLE = 1e-9
INFEASIBLE_TOLERANCE = 1e-6
MAX_PIVOTS = 2000


@dataclass
class CanonicalForm:
    """Sistema en igualdad generado por Big-M (forma max tras negar si hace falta)."""
    matrix: np.ndarray
    rhs: np.ndarray
    costs: np.ndarray
    column_labels: tuple[str, ...]
    basis_names: tuple[str, ...]
    basis_indices: list[int]
    big_m: float
    is_max_form: bool
    artificial_labels: frozenset[str]

    @property
    def num_rows(self) -> int:
        return self.matrix.shape[0]

    @property
    def num_columns(self) -> int:
        return self.matrix.shape[1]


@dataclass
class SimplexStep:
    kind: str
    column_labels: tuple[str, ...]
    basis_names: tuple[str, ...]
    matrix: np.ndarray
    reduced_costs: tuple[float, ...]
    objective_value: float
    entering: str | None
    leaving: str | None
    pivot_row: int | None
    pivot_col: int | None
    pivot_value: float | None
    ratios: tuple[float | None, ...]
    solution: dict[str, float] = field(default_factory=dict)
    note: str = field(default="")


@dataclass
class SimplexResult:
    steps: tuple[SimplexStep, ...]
    status: str
    objective_value: float
    solution: dict[str, float]
    sense: str
    big_m: float
    num_iterations: int
    canonical: CanonicalForm


def _infer_big_m(problem: LPProblem, costs_max: np.ndarray, rhs: np.ndarray, coeff_matrix: np.ndarray) -> float:
    objective_scale = float(np.abs(costs_max).sum())
    rhs_scale = float(np.abs(rhs).sum())
    row_scale = float(np.abs(coeff_matrix).sum(axis=1).max()) if coeff_matrix.size else 0.0
    return 1.0 + objective_scale + rhs_scale + row_scale


def _build_canonical_form(problem: LPProblem, big_m: float | None) -> CanonicalForm:
    num_variables = problem.num_variables
    num_constraints = problem.num_constraints
    is_max_form = problem.objective_sense == "max"
    costs_max = np.array(problem.objective_coeffs, dtype=float)
    if not is_max_form:
        costs_max = -costs_max

    slack_columns = sum(c.relation == "<=" for c in problem.constraints)
    surplus_columns = sum(c.relation == ">=" for c in problem.constraints)
    artificial_columns = sum(c.relation != "<=" for c in problem.constraints)

    num_total = num_variables + slack_columns + surplus_columns + artificial_columns
    matrix = np.zeros((num_constraints, num_total), dtype=float)
    rhs = np.array([constraint.rhs for constraint in problem.constraints], dtype=float)

    variable_labels = [f"x{i + 1}" for i in range(num_variables)]
    slack_labels = [f"s{i + 1}" for i in range(slack_columns)]
    surplus_labels = [f"e{i + 1}" for i in range(surplus_columns)]
    artificial_labels_list = [f"a{i + 1}" for i in range(artificial_columns)]
    labels = variable_labels + slack_labels + surplus_labels + artificial_labels_list

    if big_m is None:
        base_coeffs = np.array(
            [[coef for coef in constraint.coefficients] for constraint in problem.constraints],
            dtype=float,
        )
        big_m = _infer_big_m(problem, costs_max, rhs, base_coeffs)

    costs = np.zeros(num_total, dtype=float)
    costs[:num_variables] = costs_max
    costs[num_variables + slack_columns + surplus_columns:] = -big_m

    basis_names: list[str] = []
    basis_indices: list[int] = []
    artificial_labels: set[str] = set()

    slack_index = num_variables
    surplus_index = slack_index + slack_columns
    artificial_index = surplus_index + surplus_columns
    slack_count = 0
    surplus_count = 0
    artificial_count = 0

    for row, constraint in enumerate(problem.constraints):
        matrix[row, :num_variables] = constraint.coefficients
        relation = constraint.relation
        if relation == "<=":
            matrix[row, slack_index] = 1.0
            basis_names.append(slack_labels[slack_count])
            basis_indices.append(slack_index)
            slack_index += 1
            slack_count += 1
        elif relation == ">=":
            matrix[row, surplus_index] = -1.0
            surplus_index += 1
            surplus_count += 1
            matrix[row, artificial_index] = 1.0
            label = artificial_labels_list[artificial_count]
            artificial_labels.add(label)
            basis_names.append(label)
            basis_indices.append(artificial_index)
            artificial_index += 1
            artificial_count += 1
        else:
            matrix[row, artificial_index] = 1.0
            label = artificial_labels_list[artificial_count]
            artificial_labels.add(label)
            basis_names.append(label)
            basis_indices.append(artificial_index)
            artificial_index += 1
            artificial_count += 1

    return CanonicalForm(
        matrix=matrix,
        rhs=rhs,
        costs=costs,
        column_labels=tuple(labels),
        basis_names=basis_names,
        basis_indices=basis_indices,
        big_m=big_m,
        is_max_form=is_max_form,
        artificial_labels=frozenset(artificial_labels),
    )


def _build_objective_row(canonical: CanonicalForm) -> np.ndarray:
    basic_costs = canonical.costs[canonical.basis_indices]
    implied_costs = basic_costs @ canonical.matrix
    reduced_row = implied_costs - canonical.costs
    objective_value = float(basic_costs @ canonical.rhs)
    return np.append(reduced_row, objective_value)


def _extract_solution(canonical: CanonicalForm, tree_rhs: np.ndarray) -> dict[str, float]:
    solution = {}
    for row, basis_col in enumerate(canonical.basis_indices):
        solution[canonical.column_labels[basis_col]] = float(tree_rhs[row])
    for label in canonical.column_labels:
        solution.setdefault(label, 0.0)
    return solution


def _original_solution(canonical: CanonicalForm, solution: dict[str, float]) -> dict[str, float]:
    original_names = [label for label in canonical.column_labels if label.startswith("x")]
    return {name: solution[name] for name in original_names}


def _display_objective(canonical: CanonicalForm, internal_value: float) -> float:
    return internal_value if canonical.is_max_form else -internal_value


def _perform_pivot(matrix: np.ndarray, pivot_row: int, pivot_col: int) -> None:
    pivot_value = matrix[pivot_row, pivot_col]
    matrix[pivot_row] = matrix[pivot_row] / pivot_value
    for row in range(matrix.shape[0]):
        if row == pivot_row:
            continue
        factor = matrix[row, pivot_col]
        if abs(factor) > NEGLIGIBLE:
            matrix[row] = matrix[row] - factor * matrix[pivot_row]


def _pick_entering_column(canonical: CanonicalForm, objective_row: np.ndarray) -> int | None:
    nonbasic = [i for i in range(canonical.num_columns) if i not in set(canonical.basis_indices)]
    candidates = [i for i in nonbasic if objective_row[i] < -NEGLIGIBLE]
    if not candidates:
        return None
    return min(candidates, key=lambda i: (objective_row[i], i))


def _ratio_test(canonical: CanonicalForm, matrix: np.ndarray, entering_col: int) -> tuple[list[float | None], int | None]:
    ratios: list[float | None] = []
    best_row: int | None = None
    best_ratio = float("inf")
    for row in range(canonical.num_rows):
        coefficient = matrix[row, entering_col]
        rhs_value = matrix[row, -1]
        if coefficient > NEGLIGIBLE:
            ratio = rhs_value / coefficient
            ratios.append(ratio)
            if ratio < best_ratio:
                best_ratio = ratio
                best_row = row
        else:
            ratios.append(None)
    return ratios, best_row


def _artificial_remains_in_basis(canonical: CanonicalForm, matrix: np.ndarray) -> bool:
    return any(
        canonical.column_labels[col] in canonical.artificial_labels
        and matrix[row, -1] > INFEASIBLE_TOLERANCE
        for row, col in enumerate(canonical.basis_indices)
    )


class BigMSolver:
    def __init__(self, problem: LPProblem, big_m: float | None = None):
        self._problem = normalize_problem(problem)
        self._big_m = big_m

    def solve(self) -> SimplexResult:
        canonical = _build_canonical_form(self._problem, self._big_m)
        object_row = _build_objective_row(canonical)
        constraint_rows = np.vstack([canonical.matrix, object_row[:-1]])
        rhs_column = np.append(canonical.rhs, object_row[-1])[:, None]
        tableau = np.hstack([constraint_rows, rhs_column])

        steps: list[SimplexStep] = []
        steps.append(
            self._make_step(
                canonical, tableau, kind="build", ratios=[], entering=None,
                leaving=None, pivot_row=None, pivot_col=None, note="",
            )
        )

        status = "optimal"
        num_pivots = 0
        for _ in range(MAX_PIVOTS):
            objective_row = tableau[-1, :-1]
            entering_col = _pick_entering_column(canonical, objective_row)
            if entering_col is None:
                break
            entering_name = canonical.column_labels[entering_col]
            ratios, leaving_row = _ratio_test(canonical, tableau, entering_col)
            if leaving_row is None:
                steps.append(
                    self._make_step(
                        canonical, tableau, kind="unbounded", ratios=ratios,
                        entering=entering_name, leaving=None, pivot_row=None,
                        pivot_col=entering_col, note="",
                    )
                )
                status = "unbounded"
                break
            leaving_name = canonical.basis_names[leaving_row]
            pivot_value = tableau[leaving_row, entering_col]
            steps.append(
                self._make_step(
                    canonical, tableau, kind="iterate", ratios=ratios,
                    entering=entering_name, leaving=leaving_name,
                    pivot_row=leaving_row, pivot_col=entering_col, note="",
                )
            )
            _perform_pivot(tableau, leaving_row, entering_col)
            canonical.basis_names[leaving_row] = entering_name
            canonical.basis_indices[leaving_row] = entering_col
            num_pivots += 1

        if status == "optimal" and _artificial_remains_in_basis(canonical, tableau):
            status = "infeasible"

        if status == "optimal":
            final_kind = "optimal"
        elif status == "infeasible":
            final_kind = "infeasible"
        else:
            final_kind = "unbounded"
        steps.append(
            self._make_step(
                canonical, tableau, kind=final_kind, ratios=[], entering=None,
                leaving=None, pivot_row=None, pivot_col=None, note=status,
            )
        )

        final_solution = _extract_solution(canonical, tableau[:-1, -1])
        internal_objective = float(tableau[-1, -1])
        canonical_matrix = tableau[:-1, :-1]
        canonical_rhs = tableau[:-1, -1].copy()
        result_form = CanonicalForm(
            matrix=canonical_matrix,
            rhs=canonical_rhs,
            costs=canonical.costs,
            column_labels=canonical.column_labels,
            basis_names=list(canonical.basis_names),
            basis_indices=list(canonical.basis_indices),
            big_m=canonical.big_m,
            is_max_form=canonical.is_max_form,
            artificial_labels=canonical.artificial_labels,
        )
        return SimplexResult(
            steps=tuple(steps),
            status=status,
            objective_value=_display_objective(canonical, internal_objective),
            solution=_original_solution(canonical, final_solution),
            sense=self._problem.objective_sense,
            big_m=canonical.big_m,
            num_iterations=num_pivots,
            canonical=result_form,
        )

    def _make_step(
        self,
        canonical: CanonicalForm,
        tableau: np.ndarray,
        kind: str,
        ratios: list[float | None],
        entering: str | None,
        leaving: str | None,
        pivot_row: int | None,
        pivot_col: int | None,
        note: str,
    ) -> SimplexStep:
        objective_row = tableau[-1, :-1]
        internal_value = float(tableau[-1, -1])
        rhs = tableau[:-1, -1].copy()
        solution = _extract_solution(canonical, rhs)
        return SimplexStep(
            kind=kind,
            column_labels=canonical.column_labels,
            basis_names=list(canonical.basis_names),
            matrix=tableau.copy(),
            reduced_costs=tuple(-(objective_row)),
            objective_value=_display_objective(canonical, internal_value),
            entering=entering,
            leaving=leaving,
            pivot_row=pivot_row,
            pivot_col=pivot_col,
            pivot_value=float(tableau[pivot_row, pivot_col]) if pivot_row is not None else None,
            ratios=tuple(ratios),
            solution=solution,
            note=note,
        )