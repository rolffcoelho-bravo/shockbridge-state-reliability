"""Deterministic synthetic proof for the Milestone 0 timing controls."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone

from shockbridge_state_risk.temporal import (
    MaturedLabel,
    TimedObservation,
    assert_point_in_time,
    labels_matured_by,
)


@dataclass(frozen=True)
class SyntheticReplay:
    events: int
    states: dict[str, int]
    matured_labels_at_cutoff: int
    checksum: str
    evidence_status: str = "SYNTHETIC_ONLY"


def run_synthetic_replay() -> SyntheticReplay:
    """Exercise timing and maturity gates without making an empirical claim."""
    base = datetime(2020, 1, 30, 12, 0, tzinfo=timezone.utc)
    observations: list[TimedObservation] = []
    labels: list[MaturedLabel] = []
    states = {"normal": 0, "stress": 0}

    for index in range(12):
        decision = base + timedelta(days=35 * index)
        state = "stress" if index in {4, 5, 9} else "normal"
        states[state] += 1
        observations.append(
            TimedObservation(
                series_id="synthetic_stress_index",
                observation_timestamp=decision - timedelta(days=1),
                first_usable_timestamp=decision - timedelta(hours=6),
                decision_timestamp=decision,
                vintage=f"v{index:02d}",
            )
        )
        labels.append(
            MaturedLabel(
                origin_timestamp=decision,
                maturity_timestamp=decision + timedelta(days=5),
                value=float(index % 3 == 0),
            )
        )

    assert_point_in_time(observations)
    cutoff = labels[-1].origin_timestamp + timedelta(days=2)
    matured = labels_matured_by(labels, cutoff)
    payload = {
        "observations": [asdict(item) for item in observations],
        "matured_origins": [item.origin_timestamp for item in matured],
        "states": states,
    }
    encoded = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return SyntheticReplay(
        events=len(observations),
        states=states,
        matured_labels_at_cutoff=len(matured),
        checksum=hashlib.sha256(encoded).hexdigest(),
    )
