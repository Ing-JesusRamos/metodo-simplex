import tkinter as tk
from tkinter import ttk

from simplex.validate import EXAMPLE_PROBLEM, build_problem, parse_float
from simplex.big_m import BigMSolver
from simplex.problem import LPProblem
from gui.state import AppState


class ProblemForm(ttk.Frame):
    def __init__(self, master: tk.Widget, state: AppState, on_solved, on_cancel):
        super().__init__(master, padding=14)
        self._state = state
        self._on_solved = on_solved
        self._on_cancel = on_cancel
        self._row_widgets: list[tuple[list[tk.StringVar], tk.StringVar, tk.StringVar]] = []
        self._build_layout()

    def _build_layout(self) -> None:
        header = ttk.Frame(self)
        header.pack(fill="x")
        ttk.Button(header, text="← Volver al inicio", command=self._on_cancel).pack(side="left")
        ttk.Label(header, text="Formulario del problema", font=("Segoe UI", 14, "bold")).pack(side="left", padx=12)
        ttk.Button(header, text="Cargar ejemplo", command=self._load_example).pack(side="right")

        controls = ttk.LabelFrame(self, text="Definición general", padding=10)
        controls.pack(fill="x", pady=(10, 6))

        self._sense_var = tk.StringVar(value="max")
        sense_frame = ttk.Frame(controls)
        sense_frame.pack(side="left", padx=(0, 24))
        ttk.Label(sense_frame, text="Objetivo:").pack(anchor="w")
        ttk.Radiobutton(sense_frame, text="Maximizar Z", variable=self._sense_var, value="max").pack(anchor="w")
        ttk.Radiobutton(sense_frame, text="Minimizar Z", variable=self._sense_var, value="min").pack(anchor="w")

        size_frame = ttk.Frame(controls)
        size_frame.pack(side="left")
        ttk.Label(size_frame, text="Número de variables").grid(row=0, column=0, padx=4, pady=2)
        ttk.Label(size_frame, text="Número de restricciones").grid(row=0, column=1, padx=4, pady=2)
        self._n_vars = tk.IntVar(value=2)
        self._n_constraints = tk.IntVar(value=2)
        ttk.Spinbox(size_frame, from_=1, to=10, textvariable=self._n_vars, width=6).grid(row=1, column=0, padx=4)
        ttk.Spinbox(size_frame, from_=1, to=20, textvariable=self._n_constraints, width=6).grid(row=1, column=1, padx=4)
        ttk.Button(size_frame, text="Generar campos", command=self._rebuild_grid).grid(row=1, column=2, padx=12)

        self._form_area = ttk.LabelFrame(self, text="Restricciones", padding=8)
        self._form_area.pack(fill="both", expand=True, pady=6)

        action_row = ttk.Frame(self)
        action_row.pack(fill="x", pady=(6, 0))
        self._status_label = ttk.Label(action_row, text="", foreground="#8a2be2", wraplength=760)
        self._status_label.pack(side="left")
        ttk.Button(action_row, text="Resolver con el método simplex", command=self._resolve).pack(side="right")

        self._rebuild_grid()

    def _rebuild_grid(self) -> None:
        for child in self._form_area.winfo_children():
            child.destroy()
        self._row_widgets = []
        self._objective_vars: list[tk.StringVar] = []

        try:
            num_variables = max(1, int(self._n_vars.get()))
            num_constraints = max(1, int(self._n_constraints.get()))
        except (tk.TclError, ValueError):
            self._status_label.config(text="Usa números enteros para la cantidad de variables y restricciones.")
            return

        canvas = tk.Canvas(self._form_area, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self._form_area, orient="vertical", command=canvas.yview)
        grid_frame = ttk.Frame(canvas)
        grid_frame.bind("<Configure>", lambda event: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=grid_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self._entry_width = 8
        headers = ["Variable"] + [f"x{i + 1}" for i in range(num_variables)] + ["Relación", "Término independiente (b)"]
        for column, text in enumerate(headers):
            ttk.Label(grid_frame, text=text, font=("Segoe UI", 10, "bold")).grid(row=0, column=column, padx=4, pady=6)

        ttk.Label(grid_frame, text="Función objetivo:").grid(row=1, column=0, padx=6, pady=3)
        for column in range(num_variables):
            var = tk.StringVar(value="1")
            self._objective_vars.append(var)
            ttk.Entry(grid_frame, textvariable=var, width=self._entry_width).grid(row=1, column=column + 1, padx=4, pady=3)

        for row in range(num_constraints):
            coefficient_vars = [tk.StringVar(value="1") for _ in range(num_variables)]
            relation_var = tk.StringVar(value="<=")
            rhs_var = tk.StringVar(value="1")
            ttk.Label(grid_frame, text=f"Restricción {row + 1}:").grid(row=row + 2, column=0, padx=6, pady=3)
            for column, var in enumerate(coefficient_vars, start=1):
                ttk.Entry(grid_frame, textvariable=var, width=self._entry_width).grid(
                    row=row + 2, column=column, padx=4, pady=3
                )
            ttk.Combobox(
                grid_frame,
                textvariable=relation_var,
                values=("<=", ">=", "=="),
                state="readonly",
                width=4,
            ).grid(row=row + 2, column=num_variables + 1, padx=4)
            ttk.Entry(grid_frame, textvariable=rhs_var, width=self._entry_width).grid(
                row=row + 2, column=num_variables + 2, padx=4, pady=3
            )
            self._row_widgets.append((coefficient_vars, relation_var, rhs_var))

        self._status_label.config(text=f"Completa los {num_constraints} renglones. Cada renglón es una restricción del problema.")

    def _load_example(self) -> None:
        self._sense_var.set(EXAMPLE_PROBLEM.objective_sense)
        self._n_vars.set(EXAMPLE_PROBLEM.num_variables)
        self._n_constraints.set(EXAMPLE_PROBLEM.num_constraints)
        self._rebuild_grid()
        for var, coef in zip(self._objective_vars, EXAMPLE_PROBLEM.objective_coeffs):
            var.set(_clean_number(coef))
        for (coefficient_vars, _, _), constraint in zip(self._row_widgets, EXAMPLE_PROBLEM.constraints):
            for var, coef in zip(coefficient_vars, constraint.coefficients):
                var.set(_clean_number(coef))
        for (_, relation_var, rhs_var), constraint in zip(self._row_widgets, EXAMPLE_PROBLEM.constraints):
            relation_var.set(constraint.relation)
            rhs_var.set(_clean_number(constraint.rhs))
        self._status_label.config(text="Ejemplo cargado: maximizar Z = 3·x1 + 2·x2 con dos restricciones ≤.")

    def run_example(self) -> None:
        self._load_example()
        self._resolve()

    def _collect_problem(self) -> LPProblem:
        coefficients_rows: list[list[float]] = []
        relations: list[str] = []
        right_hand_sides: list[float] = []
        for index, (coefficient_vars, relation_var, rhs_var) in enumerate(self._row_widgets):
            row = []
            for position, var in enumerate(coefficient_vars, start=1):
                row.append(parse_float(var.get(), f"coeficiente de x{position} en la restricción {index + 1}"))
            coefficients_rows.append(row)
            relations.append(relation_var.get())
            right_hand_sides.append(parse_float(rhs_var.get(), f"término independiente de la restricción {index + 1}"))
        objective = [
            parse_float(var.get(), f"coeficiente de x{position} en la función objetivo")
            for position, var in enumerate(self._objective_vars, start=1)
        ]
        return build_problem(self._sense_var.get(), objective, coefficients_rows, relations, right_hand_sides)

    def _resolve(self) -> None:
        try:
            problem = self._collect_problem()
        except ValueError as error:
            self._status_label.config(text=f"Revisa la entrada: {error}", foreground="#c0392b")
            return
        self._status_label.config(text="Resolviendo...", foreground="#2c7a7b")
        self.update_idletasks()
        result = BigMSolver(problem).solve()
        self._state.problem = problem
        self._state.result = result
        self._on_solved()


def _clean_number(value: float) -> str:
    if abs(value - round(value)) < 1e-9:
        return str(int(round(value)))
    return f"{value:g}"