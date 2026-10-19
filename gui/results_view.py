import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from gui.state import AppState
from explain import glossary
from explain.step_explanations import explain_step, interpret_solution, LEVELS
from explain import graph_explanations as graph_explain
from viz import plots

FIXED_FONT = ("Consolas", 10)
UI_FONT = ("Segoe UI", 10)

_TERM_TAG_PREFIX = "glossary-term::"
LEVEL_LABELS = {"basico": "Básico (sencillo)", "intermedio": "Intermedio", "tecnico": "Técnico (con fórmulas)"}


class ResultsView(ttk.Frame):
    def __init__(self, master: tk.Widget, state: AppState, on_back):
        super().__init__(master, padding=10)
        self._state = state
        self._on_back = on_back
        self._step_index = 0
        self._level_var = tk.StringVar(value="basico")
        self._canvas_refs: list = []
        self._build_widgets()

    def _build_widgets(self) -> None:
        header = ttk.Frame(self)
        header.pack(fill="x")
        ttk.Button(header, text="← Editar problema", command=self._on_back).pack(side="left")
        self._header_label = ttk.Label(header, font=("Segoe UI", 13, "bold"))
        self._header_label.pack(side="left", padx=12)

        self._notebook = ttk.Notebook(self)
        self._notebook.pack(fill="both", expand=True, pady=(8, 0))

        self._solution_tab = ttk.Frame(self._notebook, padding=8)
        self._steps_tab = ttk.Frame(self._notebook, padding=8)
        self._graphs_tab = ttk.Frame(self._notebook, padding=8)
        self._glossary_tab = ttk.Frame(self._notebook, padding=8)
        self._notebook.add(self._solution_tab, text="Solución")
        self._notebook.add(self._steps_tab, text="Método paso a paso")
        self._notebook.add(self._graphs_tab, text="Gráficas")
        self._notebook.add(self._glossary_tab, text="Glosario")

        self._build_solution_tab()
        self._build_steps_tab()
        self._build_graphs_tab()
        self._build_glossary_tab()

    # ---------------------------------------------------------- Solución
    def _build_solution_tab(self) -> None:
        self._problem_text = ScrolledText(self._solution_tab, height=4, wrap="word", font=UI_FONT)
        self._problem_text.pack(fill="x")
        self._problem_text.configure(state="disabled")

        panes = ttk.Panedwindow(self._solution_tab, orient="horizontal")
        panes.pack(fill="both", expand=True, pady=(6, 0))
        left = ttk.Frame(panes)
        right = ttk.Frame(panes)
        panes.add(left, weight=1)
        panes.add(right, weight=1)

        self._interpretation_text = ScrolledText(left, wrap="word", font=UI_FONT, height=8)
        self._interpretation_text.pack(fill="both", expand=True)
        self._interpretation_text.configure(state="disabled")

        self._graph_area = ttk.Frame(right)
        self._graph_area.pack(fill="both", expand=True)
        self._graph_explanation = ScrolledText(right, wrap="word", font=UI_FONT, height=6)
        self._graph_explanation.pack(fill="x")
        self._graph_explanation.configure(state="disabled")

    # --------------------------------------------------- Paso a paso
    def _build_steps_tab(self) -> None:
        controls = ttk.Frame(self._steps_tab)
        controls.pack(fill="x", pady=(0, 6))
        self._prev_button = ttk.Button(controls, text="← Anterior", command=self._prev_step)
        self._prev_button.pack(side="left")
        self._next_button = ttk.Button(controls, text="Siguiente →", command=self._next_step)
        self._next_button.pack(side="left", padx=6)
        self._step_label = ttk.Label(controls, font=("Segoe UI", 11, "bold"))
        self._step_label.pack(side="left", padx=10)

        ttk.Label(controls, text="Nivel de explicación:").pack(side="right")
        self._level_box = ttk.Combobox(
            controls,
            textvariable=self._level_var,
            values=[LEVEL_LABELS[level] for level in LEVELS],
            state="readonly",
            width=22,
        )
        self._level_box.pack(side="right", padx=6)
        self._level_box.bind("<<ComboboxSelected>>", lambda event: self._render_step())

        table_frame = ttk.LabelFrame(self._steps_tab, text="Tableau (tabla simplex)", padding=4)
        table_frame.pack(fill="x", pady=(0, 6))
        self._tableau_text = tk.Text(
            table_frame, font=FIXED_FONT, height=8, wrap="none", background="#fafafa", relief="sunken"
        )
        tableau_scroll_y = ttk.Scrollbar(table_frame, orient="vertical", command=self._tableau_text.yview)
        tableau_scroll_x = ttk.Scrollbar(table_frame, orient="horizontal", command=self._tableau_text.xview)
        self._tableau_text.configure(
            yscrollcommand=tableau_scroll_y.set, xscrollcommand=tableau_scroll_x.set
        )
        self._tableau_text.grid(row=0, column=0, sticky="nsew")
        tableau_scroll_y.grid(row=0, column=1, sticky="ns")
        tableau_scroll_x.grid(row=1, column=0, sticky="ew")
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)

        self._ratio_label = ttk.Label(self._steps_tab, text="", font=UI_FONT, foreground="#2c5282", wraplength=1000)
        self._ratio_label.pack(fill="x", pady=(0, 4))

        self._step_explanation = ScrolledText(self._steps_tab, wrap="word", font=UI_FONT)
        self._step_explanation.pack(fill="both", expand=True)
        self._step_explanation.configure(state="disabled")

        self._term_label = ttk.Label(self._steps_tab, text="", font=UI_FONT, foreground="#6b21a8", wraplength=1000)
        self._term_label.pack(fill="x", pady=(4, 0))

    # -------------------------------------------------------- Gráficas
    def _build_graphs_tab(self) -> None:
        self._graphs_notebook = ttk.Notebook(self._graphs_tab)
        self._graphs_notebook.pack(fill="both", expand=True)
        self._region_tab = ttk.Frame(self._graphs_notebook, padding=6)
        self._progress_tab = ttk.Frame(self._graphs_notebook, padding=6)
        self._graphs_notebook.add(self._region_tab, text="Región factible")
        self._graphs_notebook.add(self._progress_tab, text="Progreso del objetivo")
        self._region_graph = ttk.Frame(self._region_tab)
        self._region_graph.pack(fill="both", expand=True)
        self._region_explanation = ScrolledText(self._region_tab, wrap="word", font=UI_FONT, height=5)
        self._region_explanation.pack(fill="x")
        self._region_explanation.configure(state="disabled")
        self._progress_graph = ttk.Frame(self._progress_tab)
        self._progress_graph.pack(fill="both", expand=True)
        self._progress_explanation = ScrolledText(self._progress_tab, wrap="word", font=UI_FONT, height=5)
        self._progress_explanation.pack(fill="x")
        self._progress_explanation.configure(state="disabled")

    # ------------------------------------------------------- Glosario
    def _build_glossary_tab(self) -> None:
        panes = ttk.Panedwindow(self._glossary_tab, orient="horizontal")
        panes.pack(fill="both", expand=True)
        left = ttk.Frame(panes)
        right = ttk.Frame(panes)
        panes.add(left, weight=1)
        panes.add(right, weight=2)
        self._glossary_list = tk.Listbox(left, font=UI_FONT)
        scrollbar = ttk.Scrollbar(left, orient="vertical", command=self._glossary_list.yview)
        self._glossary_list.configure(yscrollcommand=scrollbar.set)
        self._glossary_list.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self._glossary_list.bind("<<ListboxSelect>>", lambda event: self._show_glossary_entry())
        self._glossary_text = ScrolledText(right, wrap="word", font=UI_FONT)
        self._glossary_text.pack(fill="both", expand=True)
        self._glossary_text.configure(state="disabled")
        for term in glossary.GLOSSARY:
            self._glossary_list.insert("end", term)

    # ------------------------------------------------------- Render
    def render(self) -> None:
        self._canvas_refs.clear()
        self._step_index = 0
        self._level_var.set(self._state.level if self._state.level in LEVEL_LABELS else "basico")
        self._render_header()
        self._render_solution_tab()
        self._render_steps_tab()
        self._render_graphs_tab()

    def _render_header(self) -> None:
        problem = self._state.problem
        result = self._state.result
        title = "Resultados"
        if problem is not None:
            mode_label = "Maximizar" if problem.objective_sense == "max" else "Minimizar"
            title = f"{mode_label} Z"
        if result is not None:
            status_names = {"optimal": "— Óptimo", "infeasible": "— Infactible", "unbounded": "— No acotado"}
            title += f" {status_names.get(result.status, '')}"
        self._header_label.config(text=title)

    # ------------------------------------------------ Solución tab
    def _render_solution_tab(self) -> None:
        problem = self._state.problem
        result = self._state.result
        if problem is None or result is None:
            return
        self._set_text(self._problem_text, _problem_statement(problem))

        self._set_text(self._interpretation_text, interpret_solution(result))

        for child in self._graph_area.winfo_children():
            child.destroy()
        num_vars = problem.num_variables
        if num_vars == 2:
            figure = plots.feasible_region_figure(problem, result.solution, result.status)
            self._embed(self._graph_area, figure)
            explanation = graph_explain.feasible_region_2d(self._current_level())
        elif num_vars == 3:
            figure = plots.surface_3d_figure(problem, result.solution, result.status)
            self._embed(self._graph_area, figure)
            explanation = graph_explain.feasible_region_3d(self._current_level())
        else:
            explanation = "La gráfica de la región factible está disponible para problemas con 2 o 3 variables."
            ttk.Label(self._graph_area, text=explanation, wraplength=400).pack(pady=30)
        if num_vars in (2, 3) and result.status == "optimal" and _has_alternate_optima(result):
            explanation += "\n\n" + graph_explain.alternate_optima_note()
        self._set_text(self._graph_explanation, explanation)

    # ---------------------------------------------- Paso a paso tab
    def _render_steps_tab(self) -> None:
        result = self._state.result
        if result is None:
            return
        total = len(result.steps)
        if self._step_index >= total:
            self._step_index = total - 1
        step = result.steps[self._step_index]
        self._prev_button.configure(state="normal" if self._step_index > 0 else "disabled")
        self._next_button.configure(state="normal" if self._step_index < total - 1 else "disabled")
        self._step_label.config(text=f"Paso {self._step_index + 1} de {total}")

        self._render_tableau(step)
        self._render_step_explanation(step)

    def _current_level(self) -> str:
        raw = self._level_var.get()
        for level, label in LEVEL_LABELS.items():
            if label == raw:
                return level
        return "basico"

    def _render_step_explanation(self, step) -> None:
        explanation = explain_step(step, self._state.problem, self._state.result, self._current_level())
        self._set_text(self._step_explanation, explanation)
        self._tag_terms(self._step_explanation)
        self._term_label.config(text="Pulsa sobre cualquier término azul para ver su definición.")

    def _render_tableau(self, step) -> None:
        self._tableau_text.configure(state="normal")
        self._tableau_text.delete("1.0", "end")
        for tag in self._tableau_text.tag_names():
            self._tableau_text.tag_delete(tag)

        has_ratio = step.kind == "iterate"
        rows, cell_offsets = _build_tableau_cells(step, has_ratio)

        for row_index, (cells, offsets) in enumerate(zip(rows, cell_offsets)):
            line = "".join(cells)
            self._tableau_text.insert("end", line + "\n")
            if row_index == 0:
                self._tableau_text.tag_add("header", f"{row_index + 1}.0", f"{row_index + 1}.{len(line)}")
                continue

            is_objective_row = row_index == len(rows) - 1
            if not is_objective_row:
                if step.pivot_row is not None and row_index - 1 == step.pivot_row:
                    self._tableau_text.tag_add("leaving", f"{row_index + 1}.0", f"{row_index + 1}.{len(line)}")
            for column_index, (start, end) in enumerate(offsets):
                if not is_objective_row and column_index - 1 == step.pivot_col and step.pivot_row is not None:
                    if row_index - 1 == step.pivot_row:
                        self._tableau_text.tag_add("pivot", f"{row_index + 1}.{start}", f"{row_index + 1}.{end}")
                        continue
                if column_index - 1 == step.pivot_col and step.pivot_col is not None:
                    self._tableau_text.tag_add("entering", f"{row_index + 1}.{start}", f"{row_index + 1}.{end}")

        self._tableau_text.tag_configure("header", font=("Consolas", 10, "bold"))
        self._tableau_text.tag_configure("entering", background="#fff3b0")
        self._tableau_text.tag_configure("leaving", background="#ffd6d6")
        self._tableau_text.tag_configure("pivot", background="#a5d6a7", font=("Consolas", 10, "bold"))
        self._tableau_text.tag_raise("pivot")
        self._tableau_text.configure(state="disabled")

        if has_ratio and step.ratios:
            rows_info = "\n".join(
                f"{name}: b/a = {_fmt(ratio) if ratio is not None else '—'}"
                for name, ratio in zip(step.basis_names, step.ratios)
            )
            self._ratio_label.config(
                text=f"Test del cociente (qué variable sale):\n{rows_info}\n"
                f"Sale {step.leaving} (mínimo de los cocientes válidos)."
            )
        else:
            self._ratio_label.config(text="")

    # ------------------------------------------------ Gráficas tab
    def _render_graphs_tab(self) -> None:
        problem = self._state.problem
        result = self._state.result
        if problem is None or result is None:
            return
        num_vars = problem.num_variables
        for child in self._region_graph.winfo_children():
            child.destroy()
        if num_vars == 2:
            figure = plots.feasible_region_figure(problem, result.solution, result.status)
            self._embed(self._region_graph, figure)
            explanation = graph_explain.feasible_region_2d(self._current_level())
        elif num_vars == 3:
            figure = plots.surface_3d_figure(problem, result.solution, result.status)
            self._embed(self._region_graph, figure)
            explanation = graph_explain.feasible_region_3d(self._current_level())
        else:
            explanation = "La gráfica de la región factible está disponible para problemas con 2 o 3 variables."
            ttk.Label(self._region_graph, text=explanation, wraplength=500).pack(pady=40)
        self._set_text(self._region_explanation, explanation)

        for child in self._progress_graph.winfo_children():
            child.destroy()
        self._embed(self._progress_graph, plots.objective_progress_figure(result))
        self._set_text(self._progress_explanation, graph_explain.objective_progress(self._current_level()))

    # ------------------------------------------------ Glosario
    def _show_glossary_entry(self) -> None:
        selection = self._glossary_list.curselection()
        if not selection:
            return
        term = self._glossary_list.get(selection[0])
        entry = glossary.GLOSSARY[term]
        self._set_text(
            self._glossary_text,
            f"{term}\n\nEn palabras sencillas:\n{entry['sencillo']}\n\n"
            f"Técnicamente:\n{entry['tecnico']}",
        )

    # ------------------------------------------------- Helpers
    def _embed(self, parent: tk.Widget, figure) -> None:
        canvas = FigureCanvasTkAgg(figure, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
        self._canvas_refs.append(canvas)

    def _set_text(self, widget: tk.Text, content: str) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", content)
        widget.configure(state="disabled")

    def _tag_terms(self, widget: tk.Text) -> None:
        for existing in widget.tag_names():
            if existing.startswith(_TERM_TAG_PREFIX):
                widget.tag_delete(existing)
        for term in glossary.GLOSSARY:
            tag_name = _TERM_TAG_PREFIX + term
            widget.tag_configure(tag_name, foreground="#1d4ed8", underline=1)
            start = "1.0"
            while True:
                start = widget.search(term, start, stopindex="end", nocase=True)
                if not start:
                    break
                end = f"{start}+{len(term)}c"
                widget.tag_add(tag_name, start, end)
                start = end
            widget.tag_bind(tag_name, "<Button-1>", lambda event, name=tag_name: self._show_clicked_term(event, name))

    def _show_clicked_term(self, event, tag_name: str) -> None:
        term = tag_name[len(_TERM_TAG_PREFIX):]
        definition = glossary.lookup(term, "sencillo")
        self._term_label.config(text=f"→ {term}: {definition}")

    def _prev_step(self) -> None:
        if self._step_index > 0:
            self._step_index -= 1
            self._render_steps_tab()

    def _next_step(self) -> None:
        result = self._state.result
        if result is not None and self._step_index < len(result.steps) - 1:
            self._step_index += 1
            self._render_steps_tab()


def _problem_statement(problem) -> str:
    sense = "Maximizar" if problem.objective_sense == "max" else "Minimizar"
    objective_terms = " + ".join(f"{_fmt(coef)}·x{i + 1}" for i, coef in enumerate(problem.objective_coeffs))
    lines = [f"{sense} Z = {objective_terms}"]
    for index, constraint in enumerate(problem.constraints, start=1):
        terms = " + ".join(f"{_fmt(coef)}·x{i + 1}" for i, coef in enumerate(constraint.coefficients))
        lines.append(f"  s.a. {terms} {constraint.relation} {_fmt(constraint.rhs)}")
    lines.append("  x1, x2, ... ≥ 0")
    return "\n".join(lines)


def _fmt(value: float) -> str:
    if abs(float(value) - round(float(value))) < 1e-9:
        return str(int(round(float(value))))
    return f"{float(value):g}"


def _build_tableau_cells(step, has_ratio: bool):
    labels = list(step.column_labels)
    matrix = step.matrix

    header = [" "] + labels + ["b"]
    if has_ratio:
        header.append("b/a")

    rows = [header]
    for row_index in range(matrix.shape[0] - 1):
        row = [step.basis_names[row_index]]
        row.extend(_fmt(value) for value in matrix[row_index, :-1])
        row.append(_fmt(matrix[row_index, -1]))
        if has_ratio:
            ratio = step.ratios[row_index] if row_index < len(step.ratios) else None
            row.append(_fmt(ratio) if ratio is not None else "—")
        rows.append(row)

    objective_row = ["Z"]
    objective_row.extend(_fmt(value) for value in step.reduced_costs)
    objective_row.append(_fmt(step.objective_value))
    if has_ratio:
        objective_row.append("")
    rows.append(objective_row)

    widths = [max(len(rows[row][column]) for row in range(len(rows))) for column in range(len(rows[0]))]
    if has_ratio:
        widths[-1] = max(widths[-1], 3)

    formatted_rows = []
    offsets_list = []
    for row in rows:
        cells = [
            cell.rjust(widths[column]) if column > 0 else cell.ljust(widths[column])
            for column, cell in enumerate(row)
        ]
        offsets = []
        running = 0
        for column in range(len(cells)):
            offsets.append((running, running + widths[column]))
            running += widths[column] + 2
        formatted_rows.append("  ".join(cells))
        offsets_list.append(offsets)
    return formatted_rows, offsets_list


def _has_alternate_optima(result) -> bool:
    final_step = result.steps[-1]
    return any(
        label not in final_step.basis_names and abs(cost) < 1e-6
        for label, cost in zip(final_step.column_labels, final_step.reduced_costs)
    )