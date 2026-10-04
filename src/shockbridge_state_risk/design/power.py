"""Design-stage power and state-measurement-error simulation.

The simulation uses standardized synthetic outcomes. It is a prospective design
diagnostic, not evidence about the sign or magnitude of any empirical response.
"""

from __future__ import annotations

import math
import random
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import NormalDist
from typing import Any

import yaml

ESTIMATORS = ("oracle_hard", "misclassified_hard", "posterior_probability")


class DesignError(ValueError):
    """Raised when a design scenario or grid is malformed."""


class SingularDesignError(ArithmeticError):
    """Raised when a simulated regression has no estimable interaction."""


@dataclass(frozen=True)
class PowerScenario:
    sample_size: int
    minority_prevalence: float
    misclassification_rate: float
    standardized_interaction: float
    replicates: int = 1_000
    alpha: float = 0.05
    seed: int = 20261002

    def validate(self) -> None:
        if self.sample_size < 8:
            raise DesignError("sample_size must be at least 8.")
        if not 0.0 < self.minority_prevalence <= 0.5:
            raise DesignError("minority_prevalence must be in (0, 0.5].")
        if not 0.0 <= self.misclassification_rate < 0.5:
            raise DesignError("misclassification_rate must be in [0, 0.5).")
        if self.standardized_interaction < 0.0:
            raise DesignError("standardized_interaction must be non-negative.")
        if self.replicates < 1:
            raise DesignError("replicates must be positive.")
        if not 0.0 < self.alpha < 1.0:
            raise DesignError("alpha must be in (0, 1).")


@dataclass(frozen=True)
class EstimatorSummary:
    estimator: str
    valid_replicates: int
    rejection_rate: float
    mean_estimate: float
    bias: float
    rmse: float
    coverage_of_true_effect: float
    mean_min_state_effective_n: float
    mean_contrast_information: float


@dataclass(frozen=True)
class ScenarioResult:
    evidence_status: str
    scenario: PowerScenario
    estimators: tuple[EstimatorSummary, ...]


@dataclass(frozen=True)
class DesignGrid:
    experiment_id: str
    evidence_status: str
    seed: int
    replicates: int
    alpha: float
    power_target: float
    workers: int
    sample_sizes: dict[str, int]
    minority_prevalences: tuple[float, ...]
    misclassification_rates: tuple[float, ...]
    standardized_interactions: tuple[float, ...]


@dataclass(frozen=True)
class _Fit:
    coefficient: float
    standard_error: float


@dataclass
class _Accumulator:
    valid: int = 0
    rejected: int = 0
    covered: int = 0
    estimate_sum: float = 0.0
    squared_error_sum: float = 0.0
    min_effective_n_sum: float = 0.0
    contrast_information_sum: float = 0.0


def _as_float_tuple(value: Any, field: str) -> tuple[float, ...]:
    if not isinstance(value, list) or not value:
        raise DesignError(f"{field} must be a non-empty list.")
    if not all(isinstance(item, (int, float)) and not isinstance(item, bool) for item in value):
        raise DesignError(f"{field} must contain only numbers.")
    return tuple(float(item) for item in value)


def load_design_grid(path: Path) -> DesignGrid:
    """Load and validate a YAML design grid."""
    with path.open("r", encoding="utf-8") as stream:
        raw = yaml.safe_load(stream)
    if not isinstance(raw, dict):
        raise DesignError("The design grid root must be a mapping.")

    sizes = raw.get("sample_sizes")
    if not isinstance(sizes, dict) or not sizes:
        raise DesignError("sample_sizes must be a non-empty mapping.")
    if not all(
        isinstance(name, str)
        and name
        and isinstance(value, int)
        and not isinstance(value, bool)
        and value >= 8
        for name, value in sizes.items()
    ):
        raise DesignError("sample_sizes must map labels to integers of at least 8.")

    grid = DesignGrid(
        experiment_id=str(raw.get("experiment_id", "")),
        evidence_status=str(raw.get("evidence_status", "")),
        seed=int(raw.get("seed", 0)),
        replicates=int(raw.get("replicates", 0)),
        alpha=float(raw.get("alpha", 0.0)),
        power_target=float(raw.get("power_target", 0.0)),
        workers=int(raw.get("workers", 1)),
        sample_sizes=dict(sizes),
        minority_prevalences=_as_float_tuple(
            raw.get("minority_prevalences"), "minority_prevalences"
        ),
        misclassification_rates=_as_float_tuple(
            raw.get("misclassification_rates"), "misclassification_rates"
        ),
        standardized_interactions=_as_float_tuple(
            raw.get("standardized_interactions"), "standardized_interactions"
        ),
    )
    if not grid.experiment_id:
        raise DesignError("experiment_id must be non-empty.")
    if grid.evidence_status != "SYNTHETIC_DESIGN_ONLY":
        raise DesignError("evidence_status must be SYNTHETIC_DESIGN_ONLY.")
    if grid.replicates < 1:
        raise DesignError("replicates must be positive.")
    if not 0.0 < grid.alpha < 1.0:
        raise DesignError("alpha must be in (0, 1).")
    if not 0.0 < grid.power_target < 1.0:
        raise DesignError("power_target must be in (0, 1).")
    if grid.workers < 1:
        raise DesignError("workers must be positive.")

    for sample_size in grid.sample_sizes.values():
        for prevalence in grid.minority_prevalences:
            for misclassification in grid.misclassification_rates:
                for interaction in grid.standardized_interactions:
                    PowerScenario(
                        sample_size=sample_size,
                        minority_prevalence=prevalence,
                        misclassification_rate=misclassification,
                        standardized_interaction=interaction,
                        replicates=grid.replicates,
                        alpha=grid.alpha,
                        seed=grid.seed,
                    ).validate()
    return grid


def _invert_3x3(matrix: list[list[float]]) -> list[list[float]]:
    augmented = [
        [float(matrix[row][column]) for column in range(3)]
        + [1.0 if row == column else 0.0 for column in range(3)]
        for row in range(3)
    ]
    for column in range(3):
        pivot = max(range(column, 3), key=lambda row: abs(augmented[row][column]))
        if abs(augmented[pivot][column]) < 1e-12:
            raise SingularDesignError("The interaction design matrix is singular.")
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        divisor = augmented[column][column]
        augmented[column] = [value / divisor for value in augmented[column]]
        for row in range(3):
            if row == column:
                continue
            multiplier = augmented[row][column]
            augmented[row] = [
                value - multiplier * pivot_value
                for value, pivot_value in zip(augmented[row], augmented[column])
            ]
    return [row[3:] for row in augmented]


def _matrix_vector(matrix: list[list[float]], vector: list[float]) -> list[float]:
    return [sum(value * vector[index] for index, value in enumerate(row)) for row in matrix]


def _quadratic(vector: list[float], matrix: list[list[float]]) -> float:
    product = _matrix_vector(matrix, vector)
    return sum(left * right for left, right in zip(vector, product))


def _fit_interaction_hc3(x: list[float], state: list[float], y: list[float]) -> _Fit:
    rows = [[1.0, dose, dose * probability] for dose, probability in zip(x, state)]
    xtx = [[0.0 for _ in range(3)] for _ in range(3)]
    xty = [0.0 for _ in range(3)]
    for row, outcome in zip(rows, y):
        for left in range(3):
            xty[left] += row[left] * outcome
            for right in range(3):
                xtx[left][right] += row[left] * row[right]
    inverse = _invert_3x3(xtx)
    coefficients = _matrix_vector(inverse, xty)
    meat = [[0.0 for _ in range(3)] for _ in range(3)]
    for row, outcome in zip(rows, y):
        residual = outcome - sum(
            value * coefficient for value, coefficient in zip(row, coefficients)
        )
        leverage = min(_quadratic(row, inverse), 1.0 - 1e-10)
        adjusted_squared = (residual / (1.0 - leverage)) ** 2
        for left in range(3):
            for right in range(3):
                meat[left][right] += adjusted_squared * row[left] * row[right]

    left_product = [
        [
            sum(inverse[row][inner] * meat[inner][column] for inner in range(3))
            for column in range(3)
        ]
        for row in range(3)
    ]
    covariance = [
        [
            sum(left_product[row][inner] * inverse[inner][column] for inner in range(3))
            for column in range(3)
        ]
        for row in range(3)
    ]
    variance = covariance[2][2]
    if not math.isfinite(variance) or variance <= 0.0:
        raise SingularDesignError("The interaction variance is not positive and finite.")
    return _Fit(coefficients[2], math.sqrt(variance))


def _t_critical_approx(alpha: float, degrees_of_freedom: int) -> float:
    """Return a two-sided Student-t critical value using a standard expansion."""
    z = NormalDist().inv_cdf(1.0 - alpha / 2.0)
    df = float(degrees_of_freedom)
    first = (z**3 + z) / (4.0 * df)
    second = (5.0 * z**5 + 16.0 * z**3 + 3.0 * z) / (96.0 * df**2)
    third = (3.0 * z**7 + 19.0 * z**5 + 17.0 * z**3 - 15.0 * z) / (384.0 * df**3)
    return z + first + second + third


def _effective_sample_size(weights: list[float]) -> float:
    total = sum(weights)
    squared = sum(weight * weight for weight in weights)
    return 0.0 if squared == 0.0 else total * total / squared


def _min_effective_state_n(state: list[float]) -> float:
    return min(
        _effective_sample_size(state), _effective_sample_size([1.0 - item for item in state])
    )


def _contrast_information(state: list[float]) -> float:
    mean = sum(state) / len(state)
    return sum((item - mean) ** 2 for item in state)


def _posterior_state_probability(
    observed_state: list[float], prevalence: float, misclassification: float
) -> list[float]:
    observed_positive_probability = (
        prevalence * (1.0 - misclassification) + (1.0 - prevalence) * misclassification
    )
    positive_posterior = prevalence * (1.0 - misclassification) / observed_positive_probability
    negative_posterior = prevalence * misclassification / (1.0 - observed_positive_probability)
    return [positive_posterior if item == 1.0 else negative_posterior for item in observed_state]


def run_power_scenario(scenario: PowerScenario) -> ScenarioResult:
    """Simulate interaction inference under hard and probabilistic state proxies."""
    scenario.validate()
    rng = random.Random(scenario.seed)
    critical = _t_critical_approx(scenario.alpha, scenario.sample_size - 3)
    accumulators = {name: _Accumulator() for name in ESTIMATORS}

    for _ in range(scenario.replicates):
        true_state = [
            1.0 if rng.random() < scenario.minority_prevalence else 0.0
            for _ in range(scenario.sample_size)
        ]
        observed_state = [
            1.0 - item if rng.random() < scenario.misclassification_rate else item
            for item in true_state
        ]
        probability_state = _posterior_state_probability(
            observed_state,
            scenario.minority_prevalence,
            scenario.misclassification_rate,
        )
        shock = [rng.gauss(0.0, 1.0) for _ in range(scenario.sample_size)]
        outcome = [
            scenario.standardized_interaction * dose * state + rng.gauss(0.0, 1.0)
            for dose, state in zip(shock, true_state)
        ]
        states = {
            "oracle_hard": true_state,
            "misclassified_hard": observed_state,
            "posterior_probability": probability_state,
        }
        for name, state in states.items():
            try:
                fit = _fit_interaction_hc3(shock, state, outcome)
            except SingularDesignError:
                continue
            accumulator = accumulators[name]
            accumulator.valid += 1
            accumulator.estimate_sum += fit.coefficient
            error = fit.coefficient - scenario.standardized_interaction
            accumulator.squared_error_sum += error * error
            accumulator.min_effective_n_sum += _min_effective_state_n(state)
            accumulator.contrast_information_sum += _contrast_information(state)
            if abs(fit.coefficient / fit.standard_error) > critical:
                accumulator.rejected += 1
            margin = critical * fit.standard_error
            if (
                fit.coefficient - margin
                <= scenario.standardized_interaction
                <= fit.coefficient + margin
            ):
                accumulator.covered += 1

    summaries: list[EstimatorSummary] = []
    for name in ESTIMATORS:
        accumulator = accumulators[name]
        if accumulator.valid == 0:
            raise SingularDesignError(f"No valid simulations for {name}.")
        mean_estimate = accumulator.estimate_sum / accumulator.valid
        summaries.append(
            EstimatorSummary(
                estimator=name,
                valid_replicates=accumulator.valid,
                rejection_rate=accumulator.rejected / accumulator.valid,
                mean_estimate=mean_estimate,
                bias=mean_estimate - scenario.standardized_interaction,
                rmse=math.sqrt(accumulator.squared_error_sum / accumulator.valid),
                coverage_of_true_effect=accumulator.covered / accumulator.valid,
                mean_min_state_effective_n=accumulator.min_effective_n_sum / accumulator.valid,
                mean_contrast_information=accumulator.contrast_information_sum / accumulator.valid,
            )
        )
    return ScenarioResult("SYNTHETIC_DESIGN_ONLY", scenario, tuple(summaries))


def _scenario_seed(base_seed: int, indices: tuple[int, int, int, int]) -> int:
    sample_index, prevalence_index, misclassification_index, effect_index = indices
    return (
        base_seed
        + 1_000_003 * sample_index
        + 10_007 * prevalence_index
        + 101 * misclassification_index
        + effect_index
    )


def _run_labeled_scenario(item: tuple[str, PowerScenario]) -> dict[str, Any]:
    sample_label, scenario = item
    row = asdict(run_power_scenario(scenario))
    row["sample_label"] = sample_label
    return row


def run_design_grid(grid: DesignGrid) -> dict[str, Any]:
    """Run every prespecified scenario and return a JSON-serializable record."""
    scenarios: list[tuple[str, PowerScenario]] = []
    for sample_index, (sample_label, sample_size) in enumerate(grid.sample_sizes.items()):
        for prevalence_index, prevalence in enumerate(grid.minority_prevalences):
            for misclassification_index, misclassification in enumerate(
                grid.misclassification_rates
            ):
                for effect_index, interaction in enumerate(grid.standardized_interactions):
                    scenario = PowerScenario(
                        sample_size=sample_size,
                        minority_prevalence=prevalence,
                        misclassification_rate=misclassification,
                        standardized_interaction=interaction,
                        replicates=grid.replicates,
                        alpha=grid.alpha,
                        seed=_scenario_seed(
                            grid.seed,
                            (
                                sample_index,
                                prevalence_index,
                                misclassification_index,
                                effect_index,
                            ),
                        ),
                    )
                    scenarios.append((sample_label, scenario))
    if grid.workers == 1 or len(scenarios) == 1:
        results = [_run_labeled_scenario(item) for item in scenarios]
    else:
        with ProcessPoolExecutor(max_workers=grid.workers) as executor:
            results = list(executor.map(_run_labeled_scenario, scenarios))
    return {
        "experiment_id": grid.experiment_id,
        "evidence_status": grid.evidence_status,
        "design": asdict(grid),
        "results": results,
    }
