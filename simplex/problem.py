from dataclasses import dataclass

VALID_RELATIONS = ("<=", ">=", "==")
VALID_SENSES = ("max", "min")


@dataclass(frozen=True)
class Constraint:
    coefficients: tuple[float, ...]
    relation: str
    rhs: float

    def validate(self) -> None:
        if self.relation not in VALID_RELATIONS:
            raise ValueError(f"Relación inválida: {self.relation!r}")
        if all(abs(value) <= 1e-12 for value in self.coefficients) and self.rhs != 0:
            raise ValueError("La restricción tiene todos sus coeficientes en cero.")
        if any(value != value for value in self.coefficients)\
                or any(abs(value) > 1e15 for value in self.coefficients):
            raise ValueError("Coeficiente no numérico o demasiado grande.")

    @property
    def num_variables(self) -> int:
        return len(self.coefficients)


@dataclass(frozen=True)
class LPProblem:
    objective_sense: str
    objective_coeffs: tuple[float, ...]
    constraints: tuple[Constraint, ...]

    def validate(self) -> None:
        if self.objective_sense not in VALID_SENSES:
            raise ValueError("El sentido del objetivo debe ser 'max' o 'min'.")
        if not self.objective_coeffs:
            raise ValueError("Debe haber al menos una variable.")
        if not self.constraints:
            raise ValueError("Debe haber al menos una restricción.")
        expected = len(self.objective_coeffs)
        for constraint in self.constraints:
            if constraint.num_variables != expected:
                raise ValueError(
                    "Todas las restricciones deben tener la misma cantidad "
                    "de coeficientes que el objetivo."
                )
            constraint.validate()

    @property
    def num_variables(self) -> int:
        return len(self.objective_coeffs)

    @property
    def num_constraints(self) -> int:
        return len(self.constraints)