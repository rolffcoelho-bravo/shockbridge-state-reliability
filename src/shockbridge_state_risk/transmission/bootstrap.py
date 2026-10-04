"""Dependence-aware resampling contract for nested state/transmission re-estimation."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Optional

import numpy as np
from numpy.typing import NDArray

from shockbridge_state_risk.state.hmm import FloatArray

IntArray = NDArray[np.int64]


class BootstrapError(ValueError):
    """Raised when a dependence-aware bootstrap contract is invalid."""


@dataclass(frozen=True)
class MovingBlockBootstrapDraw:
    replicate: int
    block_starts: tuple[int, ...]
    observation_indices: tuple[int, ...]


@dataclass(frozen=True)
class MovingBlockBootstrapPlan:
    sample_size: int
    block_length: int
    replications: int
    random_seed: int
    draws: tuple[MovingBlockBootstrapDraw, ...]
    first_stage_requirement: str = "REFIT_STATE_MODEL_INSIDE_EVERY_REPLICATE"


@dataclass(frozen=True)
class NestedBootstrapResult:
    plan: MovingBlockBootstrapPlan
    estimates: FloatArray
    estimator_contract: str = "CALLBACK_REFITS_FIRST_STAGE_AND_TRANSMISSION_MODEL"


def make_circular_moving_block_plan(
    sample_size: int, block_length: int, replications: int, random_seed: int
) -> MovingBlockBootstrapPlan:
    """Create deterministic circular moving-block draws without touching outcomes."""
    if sample_size < 4:
        raise BootstrapError("Moving-block bootstrap requires at least four observations.")
    if block_length < 2 or block_length > sample_size:
        raise BootstrapError("Bootstrap block length must be between two and the sample size.")
    if replications < 1:
        raise BootstrapError("Bootstrap replications must be positive.")
    generator = np.random.default_rng(random_seed)
    blocks_per_draw = int(np.ceil(sample_size / block_length))
    within_block = np.arange(block_length, dtype=np.int64)
    draws: list[MovingBlockBootstrapDraw] = []
    for replicate in range(replications):
        starts = generator.integers(0, sample_size, size=blocks_per_draw, dtype=np.int64)
        indices = np.concatenate([((int(start) + within_block) % sample_size) for start in starts])[
            :sample_size
        ]
        draws.append(
            MovingBlockBootstrapDraw(
                replicate=replicate,
                block_starts=tuple(int(value) for value in starts),
                observation_indices=tuple(int(value) for value in indices),
            )
        )
    return MovingBlockBootstrapPlan(
        sample_size=sample_size,
        block_length=block_length,
        replications=replications,
        random_seed=random_seed,
        draws=tuple(draws),
    )


def evaluate_nested_bootstrap(
    plan: MovingBlockBootstrapPlan,
    refit_and_estimate: Callable[[IntArray], FloatArray],
) -> NestedBootstrapResult:
    """Evaluate a callback that refits both stages within every stored draw."""
    if len(plan.draws) != plan.replications:
        raise BootstrapError("Bootstrap plan replication count is inconsistent.")
    for draw in plan.draws:
        if len(draw.observation_indices) != plan.sample_size or any(
            index < 0 or index >= plan.sample_size for index in draw.observation_indices
        ):
            raise BootstrapError("Bootstrap plan observation indices are invalid.")
    estimates: list[FloatArray] = []
    expected_shape: Optional[tuple[int, ...]] = None
    for draw in plan.draws:
        indices = np.asarray(draw.observation_indices, dtype=np.int64)
        estimate = np.asarray(refit_and_estimate(indices), dtype=np.float64)
        if estimate.ndim != 1 or estimate.size == 0 or np.any(~np.isfinite(estimate)):
            raise BootstrapError("Nested bootstrap estimates must be finite nonempty vectors.")
        if expected_shape is None:
            expected_shape = estimate.shape
        elif estimate.shape != expected_shape:
            raise BootstrapError("Nested bootstrap estimate shapes must be constant.")
        estimates.append(estimate)
    return NestedBootstrapResult(plan=plan, estimates=np.stack(estimates))
