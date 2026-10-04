"""Point-in-time information and label-maturity controls."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime


class TemporalIntegrityError(ValueError):
    """Raised when future information would enter an estimate or decision."""


@dataclass(frozen=True)
class TimedObservation:
    series_id: str
    observation_timestamp: datetime
    first_usable_timestamp: datetime
    decision_timestamp: datetime
    vintage: str


@dataclass(frozen=True)
class MaturedLabel:
    origin_timestamp: datetime
    maturity_timestamp: datetime
    value: float


def assert_point_in_time(observations: Iterable[TimedObservation]) -> None:
    """Fail unless every observation was usable strictly before the decision."""
    violations = [
        item for item in observations if item.first_usable_timestamp >= item.decision_timestamp
    ]
    if violations:
        details = ", ".join(
            f"{item.series_id}@{item.decision_timestamp.isoformat()}" for item in violations
        )
        raise TemporalIntegrityError(f"Future information detected: {details}")


def labels_matured_by(labels: Iterable[MaturedLabel], as_of: datetime) -> tuple[MaturedLabel, ...]:
    """Return only labels whose outcome was observable by the fitting origin."""
    return tuple(label for label in labels if label.maturity_timestamp <= as_of)
