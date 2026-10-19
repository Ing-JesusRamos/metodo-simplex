"""Figuras de matplotlib para visualizar el problema y la evolución del método."""

import numpy as np
from matplotlib.figure import Figure

from simplex.problem import LPProblem

EPS = 1e-9
TOL_SCALE = 1e-6


def _plot_extent(problem: LPProblem, solution: dict[str, float]) -> float:
    candidates = [1.0]
    for constraint in problem.constraints:
        candidates.append(abs(constraint.rhs))
        for coef, rhs in zip(constraint.coefficients, [constraint.rhs]):
            if abs(coef) > EPS:
                candidates.append(abs(rhs / coef))
    candidates.extend(abs(value) for value in solution.values())
    return max(candidates) * 1.8


def _tolerance(problem: LPProblem) -> float:
    scale = max(1.0, max(abs(constraint.rhs) for constraint in problem.constraints))
    return TOL_SCALE * scale


def _feasibility_mask(grid: tuple[np.ndarray, ...], problem: LPProblem, tolerance: float) -> np.ndarray:
    mask = np.ones(grid[0].shape, dtype=bool)
    for constraint in problem.constraints:
        lhs = sum(coef * axis for coef, axis in zip(constraint.coefficients, grid))
        if constraint.relation == "<=":
            mask &= lhs <= constraint.rhs + tolerance
        elif constraint.relation == ">=":
            mask &= lhs >= constraint.rhs - tolerance
        else:
            mask &= np.abs(lhs - constraint.rhs) <= tolerance
    for axis in grid:
        mask &= axis >= -tolerance
    return mask


def _boundary_points(problem: LPProblem, extent: float) -> list[np.ndarray]:
    lines = []
    for constraint in problem.constraints:
        a1, a2 = constraint.coefficients
        if abs(a2) > EPS:
            xs = np.array([0.0, extent])
            ys = (constraint.rhs - a1 * xs) / a2
            lines.append((a1, a2, constraint.rhs))
        else:
            x_value = constraint.rhs / a1 if abs(a1) > EPS else None
            lines.append((a1, a2, constraint.rhs))
    tolerance = _tolerance(problem)

    def is_feasible(point: np.ndarray) -> bool:
        if point[0] < -tolerance or point[1] < -tolerance:
            return False
        if point[0] > extent + tolerance or point[1] > extent + tolerance:
            return False
        for constraint in problem.constraints:
            value = sum(coef * coord for coef, coord in zip(constraint.coefficients, point))
            if constraint.relation == "<=" and value > constraint.rhs + tolerance:
                return False
            if constraint.relation == ">=" and value < constraint.rhs - tolerance:
                return False
            if constraint.relation == "==" and abs(value - constraint.rhs) > tolerance:
                return False
        return True

    def intersect(first: tuple[float, float, float], second: tuple[float, float, float]) -> np.ndarray | None:
        a1, b1, c1 = first
        a2, b2, c2 = second
        determinant = a1 * b2 - a2 * b1
        if abs(determinant) < EPS:
            return None
        x = (c1 * b2 - c2 * b1) / determinant
        y = (a1 * c2 - a2 * c1) / determinant
        return np.array([x, y])

    vertical_axis = (1.0, 0.0, 0.0)
    horizontal_axis = (0.0, 1.0, 0.0)
    points = [np.array([0.0, 0.0])]
    for line in lines:
        points.extend(
            candidate
            for candidate in (
                intersect(line, vertical_axis),
                intersect(line, horizontal_axis),
            )
            if candidate is not None
        )
    for i, first in enumerate(lines):
        for second in lines[i + 1:]:
            candidate = intersect(first, second)
            if candidate is not None:
                points.append(candidate)

    seen = set()
    unique = []
    for point in points:
        key = (round(point[0], 6), round(point[1], 6))
        if key in seen or not is_feasible(point):
            continue
        seen.add(key)
        unique.append(point)
    return unique


def feasible_region_figure(problem: LPProblem, solution: dict[str, float], status: str) -> Figure:
    figure = Figure(figsize=(6.5, 5.2), dpi=100)
    axis = figure.add_subplot(111)
    extent = _plot_extent(problem, solution)
    tolerance = _tolerance(problem)

    grid_x, grid_y = np.meshgrid(
        np.linspace(0, extent, 300),
        np.linspace(0, extent, 300),
    )
    mask = _feasibility_mask((grid_x, grid_y), problem, tolerance)
    if mask.any():
        axis.contourf(grid_x, grid_y, mask.astype(float), levels=[0.5, 1.5], colors=["#bfd7ea"], alpha=0.55)

    for constraint in problem.constraints:
        a1, a2 = constraint.coefficients
        if abs(a2) > EPS:
            xs = np.linspace(0, extent, 200)
            ys = (constraint.rhs - a1 * xs) / a2
            axis.plot(xs, ys, color="#333333", linewidth=1.4)
            label_x, label_y = xs[-1], ys[-1]
        else:
            x_value = constraint.rhs / a1 if abs(a1) > EPS else extent
            axis.axvline(x_value, color="#333333", linewidth=1.4)
            label_x, label_y = x_value, extent * 0.95
        sign = {"<=": "≤", ">=": "≥", "==": "="}[constraint.relation]
        axis.text(label_x, label_y, f"{a1:.2g}x₁ + {a2:.2g}x₂ {sign} {constraint.rhs:.2g}",
                  fontsize=7, color="#222222", ha="center", va="center")

    objective = np.array(problem.objective_coeffs, dtype=float)
    objective_value = sum(coef * solution.get(f"x{i + 1}", 0.0) for i, coef in enumerate(objective))
    if abs(objective_value) > EPS:
        levels = np.linspace(objective_value * 0.15, objective_value, 6)
        if np.all(np.diff(levels) > 0):
            axis.contour(
                grid_x, grid_y,
                objective[0] * grid_x + objective[1] * grid_y,
                levels=levels,
                colors="#555555",
                linewidths=0.7,
                linestyles="dashed",
                alpha=0.6,
            )

    vertices = _boundary_points(problem, extent)
    if vertices:
        vertex_array = np.array(vertices)
        axis.scatter(vertex_array[:, 0], vertex_array[:, 1], s=12, color="#666666", zorder=3)

    optimum = np.array([solution.get("x1", 0.0), solution.get("x2", 0.0)])
    axis.scatter([optimum[0]], [optimum[1]], s=70, color="#c0392b", zorder=5, label="Óptimo")

    direction = objective
    if problem.objective_sense == "min":
        direction = -direction
    if np.linalg.norm(direction) > EPS:
        axis.annotate(
            "",
            xy=(optimum[0] + direction[0] * extent * 0.12, optimum[1] + direction[1] * extent * 0.12),
            xytext=(optimum[0], optimum[1]),
            arrowprops=dict(arrowstyle="->", color="#c0392b", lw=1.6),
        )

    status_title = {"optimal": "Solución óptima", "unbounded": "Problema no acotado",
                    "infeasible": "Problema infactible"}.get(status, status)
    axis.set_title(f"Región factible — {status_title}", fontsize=10)
    axis.set_xlabel("x₁", fontsize=9)
    axis.set_ylabel("x₂", fontsize=9)
    axis.set_xlim(0, extent)
    axis.set_ylim(0, extent)
    axis.grid(alpha=0.3, linestyle=":")
    axis.legend(loc="best", fontsize=8)
    figure.subplots_adjust(left=0.08, right=0.97, top=0.92, bottom=0.1)
    return figure


def surface_3d_figure(problem: LPProblem, solution: dict[str, float], status: str) -> Figure:
    figure = Figure(figsize=(6.5, 5.4), dpi=100)
    axis = figure.add_subplot(111, projection="3d")
    extent = _plot_extent(problem, solution)
    tolerance = _tolerance(problem)

    grid_x, grid_y, grid_z = np.meshgrid(
        np.linspace(0, extent, 24),
        np.linspace(0, extent, 24),
        np.linspace(0, extent, 24),
    )
    mask = _feasibility_mask((grid_x, grid_y, grid_z), problem, tolerance)
    axis.scatter(
        grid_x[mask], grid_y[mask], grid_z[mask],
        s=1.0, color="#4a90d9", alpha=0.35,
    )

    axis.set_xlabel("x₁", fontsize=8)
    axis.set_ylabel("x₂", fontsize=8)
    axis.set_zlabel("x₃", fontsize=8)
    axis.set_title("Región factible en 3D (arrastrar para rotar)", fontsize=10)

    optimum = np.array([solution.get(f"x{i + 1}", 0.0) for i in range(3)])
    axis.scatter([optimum[0]], [optimum[1]], [optimum[2]], s=90, color="#c0392b", zorder=5)

    objective = np.array(problem.objective_coeffs, dtype=float)
    direction = objective
    if problem.objective_sense == "min":
        direction = -direction
    if np.linalg.norm(direction) > EPS:
        axis.quiver(
            optimum[0], optimum[1], optimum[2],
            direction[0] * extent * 0.25, direction[1] * extent * 0.25, direction[2] * extent * 0.25,
            color="#c0392b", arrow_length_ratio=0.18,
        )
    figure.subplots_adjust(left=0.02, right=0.98, top=0.94, bottom=0.05)
    return figure


def objective_progress_figure(result) -> Figure:
    figure = Figure(figsize=(6.5, 4.2), dpi=100)
    axis = figure.add_subplot(111)
    values = [step.objective_value for step in result.steps if step.kind != "build"]
    if not values:
        values = [result.objective_value]
    indices = list(range(len(values)))
    axis.plot(indices, values, marker="o", color="#2980b9", linewidth=2)
    axis.set_title("Evolución de la función objetivo por iteración", fontsize=10)
    axis.set_xlabel("Iteración", fontsize=9)
    axis.set_ylabel("Z", fontsize=9)
    axis.grid(alpha=0.3, linestyle=":")
    axis.axhline(result.objective_value, color="#c0392b", linestyle="--", alpha=0.6)
    axis.annotate(
        f"Z* = {result.objective_value:.4g}",
        xy=(indices[-1], values[-1]),
        xytext=(indices[-1] - len(indices) * 0.2, values[-1] * 1.05),
        fontsize=9, color="#c0392b",
    )
    figure.subplots_adjust(left=0.08, right=0.97, top=0.9, bottom=0.12)
    return figure