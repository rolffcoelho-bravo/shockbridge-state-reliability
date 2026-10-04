import unittest

from shockbridge_state_risk.synthetic import run_synthetic_replay


class SyntheticReplayTests(unittest.TestCase):
    def test_replay_is_deterministic_and_labeled_synthetic(self) -> None:
        first = run_synthetic_replay()
        second = run_synthetic_replay()
        self.assertEqual(first, second)
        self.assertEqual(first.events, 12)
        self.assertEqual(first.states, {"normal": 9, "stress": 3})
        self.assertEqual(first.matured_labels_at_cutoff, 11)
        self.assertEqual(first.evidence_status, "SYNTHETIC_ONLY")


if __name__ == "__main__":
    unittest.main()
