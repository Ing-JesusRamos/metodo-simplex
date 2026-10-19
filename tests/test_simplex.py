import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from simplex.problem import Constraint, LPProblem
from simplex.big_m import BigMSolver

TOLERANCE = 1e-6


def _problem(sense, objective, constraints):
    return LPProblem(
        objective_sense=sense,
        objective_coeffs=tuple(float(v) for v in objective),
        constraints=tuple(
            Constraint(tuple(float(v) for v in row), relation, float(rhs))
            for row, relation, rhs in constraints
        ),
    )


def test_max_basic():
    problem = _problem(
        "max",
        (3, 2),
        [((1, 1), "<=", 4), ((2, 1), "<=", 5)],
    )
    result = BigMSolver(problem).solve()
    assert result.status == "optimal", result.status
    assert abs(result.objective_value - 9.0) < TOLERANCE
    assert abs(result.solution["x1"] - 1.0) < TOLERANCE
    assert abs(result.solution["x2"] - 3.0) < TOLERANCE


def test_min_with_ge_constraints():
    problem = _problem(
        "min",
        (2, 1),
        [((1, 1), ">=", 3), ((1, 2), ">=", 4)],
    )
    result = BigMSolver(problem).solve()
    assert result.status == "optimal", result.status
    assert abs(result.objective_value - 3.0) < TOLERANCE
    assert abs(result.solution["x1"] - 0.0) < TOLERANCE
    assert abs(result.solution["x2"] - 3.0) < TOLERANCE


def test_equality_constraint():
    problem = _problem(
        "max",
        (1, 1),
        [((1, 1), "==", 5), ((1, 0), "<=", 3)],
    )
    result = BigMSolver(problem).solve()
    assert result.status == "optimal", result.status
    assert abs(result.objective_value - 5.0) < TOLERANCE
    assert abs(result.solution["x1"] - 3.0) < TOLERANCE
    assert abs(result.solution["x2"] - 2.0) < TOLERANCE


def test_infeasible():
    problem = _problem(
        "max",
        (1, 0),
        [((1, 0), ">=", 5), ((1, 0), "<=", 3)],
    )
    result = BigMSolver(problem).solve()
    assert result.status == "infeasible", result.status


def test_unbounded():
    problem = _problem(
        "max",
        (1, 1),
        [((1, -1), "<=", 1)],
    )
    result = BigMSolver(problem).solve()
    assert result.status == "unbounded", result.status


def test_negative_rhs_normalization():
    problem = _problem(
        "max",
        (1, 1),
        [((-1, -1), ">=", -4)],
    )
    result = BigMSolver(problem).solve()
    assert result.status == "optimal", result.status
    assert abs(result.objective_value - 4.0) < TOLERANCE


def test_steps_structure():
    problem = _problem(
        "max",
        (3, 2),
        [((1, 1), "<=", 4), ((2, 1), "<=", 5)],
    )
    result = BigMSolver(problem).solve()
    assert result.steps[0].kind == "build"
    assert result.steps[-1].kind == "optimal"
    assert result.num_iterations == 2


def test_all_cases():
    test_functions = [
        test_max_basic,
        test_min_with_ge_constraints,
        test_equality_constraint,
        test_infeasible,
        test_unbounded,
        test_negative_rhs_normalization,
        test_steps_structure,
    ]
    failures = []
    for test in test_functions:
        try:
            test()
            print(f"  OK  {test.__name__}")
        except AssertionError as error:
            failures.append((test.__name__, error))
            print(f"FAIL  {test.__name__}: {error}")
    if failures:
        raise SystemExit(1)
    print(f"\nTodos los {len(test_functions)} tests pasaron.")


if __name__ == "__main__":
    test_all_cases()