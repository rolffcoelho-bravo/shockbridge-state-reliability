import unittest
from datetime import datetime, timedelta, timezone

from shockbridge_state_risk.temporal import (
    MaturedLabel,
    TemporalIntegrityError,
    TimedObservation,
    assert_point_in_time,
    labels_matured_by,
)


class TemporalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.decision = datetime(2024, 6, 6, 11, 45, tzinfo=timezone.utc)

    def test_pre_event_observation_passes(self) -> None:
        observation = TimedObservation(
            "credit_spread",
            self.decision - timedelta(days=1),
            self.decision - timedelta(hours=2),
            self.decision,
            "vintage-1",
        )
        assert_point_in_time([observation])

    def test_future_revision_fails_closed(self) -> None:
        observation = TimedObservation(
            "revised_macro_series",
            self.decision - timedelta(days=30),
            self.decision + timedelta(days=7),
            self.decision,
            "future-vintage",
        )
        with self.assertRaises(TemporalIntegrityError):
            assert_point_in_time([observation])

    def test_observation_usable_exactly_at_cutoff_fails_closed(self) -> None:
        observation = TimedObservation(
            "boundary_observation",
            self.decision - timedelta(days=1),
            self.decision,
            self.decision,
            "boundary-vintage",
        )
        with self.assertRaises(TemporalIntegrityError):
            assert_point_in_time([observation])

    def test_unmatured_outcome_is_excluded(self) -> None:
        labels = [
            MaturedLabel(self.decision, self.decision + timedelta(days=1), 0.0),
            MaturedLabel(self.decision, self.decision + timedelta(days=10), 1.0),
        ]
        available = labels_matured_by(labels, self.decision + timedelta(days=5))
        self.assertEqual(len(available), 1)
        self.assertEqual(available[0].value, 0.0)


if __name__ == "__main__":
    unittest.main()
