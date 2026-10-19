from dataclasses import dataclass

from simplex.problem import LPProblem
from simplex.big_m import SimplexResult


@dataclass
class AppState:
    mode: str = "guiado"
    level: str = "basico"
    problem: LPProblem | None = None
    result: SimplexResult | None = None