import tkinter as tk
from tkinter import ttk

from gui.state import AppState
from gui.problem_form import ProblemForm
from gui.results_view import ResultsView

MODE_LABELS = {"guiado": "Modo guiado (con explicaciones)", "experto": "Modo experto (directo)"}


class SimplexApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Método Simplex — Big-M")
        self.geometry("1160x790")
        self.minsize(980, 640)
        self.state = AppState()
        self._views: dict[str, ttk.Frame] = {}
        self._current_view: str | None = None

        self._build_nav_bar()
        self._container = ttk.Frame(self)
        self._container.pack(fill="both", expand=True)

        self._views["home"] = self._build_home()
        self._views["form"] = ProblemForm(
            self._container,
            self.state,
            on_solved=self._show_results,
            on_cancel=lambda: self._show("home"),
        )
        self._views["results"] = ResultsView(
            self._container,
            self.state,
            on_back=lambda: self._show("form"),
        )
        self._apply_mode()
        self._show("home")

    def _build_nav_bar(self) -> None:
        bar = ttk.Frame(self, padding=(10, 8))
        bar.pack(fill="x")
        ttk.Label(bar, text="Método Simplex", font=("Segoe UI", 13, "bold")).pack(side="left")
        self._nav_buttons: dict[str, ttk.Button] = {}
        for name, label in (("home", "Inicio"), ("form", "Formulario"), ("results", "Resultados")):
            button = ttk.Button(bar, text=label, command=lambda view=name: self._show(view))
            button.pack(side="left", padx=6)
            self._nav_buttons[name] = button

        ttk.Label(bar, text="Nivel:").pack(side="right", padx=(8, 0))
        self._mode_var = tk.StringVar(value="guiado")
        mode_box = ttk.Combobox(
            bar,
            textvariable=self._mode_var,
            values=list(MODE_LABELS.values()),
            state="readonly",
            width=30,
        )
        mode_box.pack(side="right")
        mode_box.bind("<<ComboboxSelected>>", lambda event: self._apply_mode())

    def _build_home(self) -> ttk.Frame:
        home = ttk.Frame(self._container, padding=30)
        ttk.Label(
            home,
            text="Bienvenido al Método Simplex",
            font=("Segoe UI", 20, "bold"),
        ).pack(anchor="w")
        ttk.Label(
            home,
            text=(
                "Este programa resuelve problemas de programación lineal con el método simplex "
                "usando la técnica Big-M. Soporta maximizar o minimizar y restricciones con ≤, ≥ y =.\n\n"
                "¿Cómo funciona? El método convierte el problema en una tabla (tableau) y, paso a paso,\n"
                "cambia de esquina de la región factible hasta encontrar la mejor. Cada paso queda\n"
                "explicado para que entiendas qué se calcula y por qué.\n\n"
                "Dos formas de usarlo:"
            ),
            font=("Segoe UI", 11),
            justify="left",
            wraplength=720,
        ).pack(anchor="w", pady=(8, 16))

        options = ttk.Frame(home)
        options.pack(anchor="w", fill="x")
        ttk.Button(
            options,
            text="Resolver mi propio problema",
            command=lambda: self._show("form"),
            width=34,
        ).pack(anchor="w", pady=4)
        ttk.Button(
            options,
            text="Ver el método con un ejemplo",
            command=self._load_example,
            width=34,
        ).pack(anchor="w", pady=4)

        ttk.Label(
            home,
            text=(
                "Consejo: si nunca usaste el método, elige 'Ver el método con un ejemplo' primero. "
                "La pestaña 'Paso a paso' te mostrará cada tabla y su explicación en lenguaje sencillo; "
                "cambia el nivel a Técnico para ver las fórmulas exactas."
            ),
            font=("Segoe UI", 10),
            foreground="#555555",
            wraplength=700,
            justify="left",
        ).pack(anchor="w", pady=(18, 0))

        ttk.Label(
            home,
            text="Los coeficientes pueden ser decimales. Los términos independientes (b) se reacomodan solos si quedan negativos.",
            font=("Segoe UI", 9),
            foreground="#999999",
        ).pack(anchor="w", pady=(12, 0))
        return home

    def _load_example(self) -> None:
        self._views["form"].run_example()
        self._show("results")

    def _apply_mode(self) -> None:
        label = self._mode_var.get()
        mode = next((key for key, value in MODE_LABELS.items() if value == label), "guiado")
        self.state.mode = mode
        self.state.level = "basico" if mode == "guiado" else "tecnico"
        if self._current_view == "results":
            self._views["results"].render()

    def _show_results(self) -> None:
        self._show("results")

    def _show(self, view_name: str) -> None:
        if self._current_view is not None:
            self._views[self._current_view].pack_forget()
        self._current_view = view_name
        view = self._views[view_name]
        view.pack(fill="both", expand=True)
        if view_name == "results":
            view.render()
        has_result = self.state.result is not None
        self._nav_buttons["results"].configure(
            state="normal" if has_result else "disabled"
        )