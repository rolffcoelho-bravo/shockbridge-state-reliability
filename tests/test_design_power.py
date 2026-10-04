import math
import tempfile
import unittest
from pathlib import Path

import yaml

from shockbridge_state_risk.design.power import (
    DesignError,
    PowerScenario,
    SingularDesignError,
    _contrast_information,
    _effective_sample_size,
    _fit_interaction_hc3,
    _invert_3x3,
    _posterior_state_probability,
    _scenario_seed,
    _t_critical_approx,
    load_design_grid,
    run_design_grid,
    run_power_scenario,
)


class DesignPowerTests(unittest.TestCase):
    def test_zero_misclassification_produces_identical_estimators(self) -> None:
        result = run_power_scenario(
            PowerScenario(
                sample_size=80,
                minority_prevalence=0.3,
                misclassification_rate=0.0,
                standardized_interaction=0.5,
                replicates=20,
                seed=3,
            )
        )
        oracle, hard, probability = result.estimators
        self.assertEqual(result.evidence_status, "SYNTHETIC_DESIGN_ONLY")
        self.assertEqual(
            oracle.__dict__ | {"estimator": "same"},
            hard.__dict__ | {"estimator": "same"},
        )
        self.assertEqual(oracle.valid_replicates, probability.valid_replicates)
        self.assertAlmostEqual(oracle.mean_estimate, probability.mean_estimate)

    def test_measurement_error_attenuates_hard_proxy(self) -> None:
        result = run_power_scenario(
            PowerScenario(
                sample_size=300,
                minority_prevalence=0.3,
                misclassification_rate=0.2,
                standardized_interaction=1.0,
                replicates=250,
                seed=7,
            )
        )
        summaries = {item.estimator: item for item in result.estimators}
        hard = summaries["misclassified_hard"]
        probability = summaries["posterior_probability"]
        self.assertLess(hard.mean_estimate, 0.8)
        self.assertLess(abs(probability.bias), abs(hard.bias))
        self.assertGreater(probability.mean_min_state_effective_n, 0.0)
        self.assertGreater(probability.mean_contrast_information, 0.0)

    def test_null_scenario_reports_rates_and_finite_diagnostics(self) -> None:
        result = run_power_scenario(PowerScenario(60, 0.2, 0.1, 0.0, replicates=30, seed=12))
        for summary in result.estimators:
            self.assertGreater(summary.valid_replicates, 0)
            self.assertGreaterEqual(summary.rejection_rate, 0.0)
            self.assertLessEqual(summary.rejection_rate, 1.0)
            self.assertTrue(math.isfinite(summary.rmse))
            self.assertEqual(summary.bias, summary.mean_estimate)

    def test_scenario_validation_rejects_invalid_fields(self) -> None:
        valid = dict(
            sample_size=20,
            minority_prevalence=0.2,
            misclassification_rate=0.1,
            standardized_interaction=0.5,
            replicates=10,
            alpha=0.05,
        )
        invalid = [
            {"sample_size": 7},
            {"minority_prevalence": 0.0},
            {"minority_prevalence": 0.6},
            {"misclassification_rate": -0.1},
            {"misclassification_rate": 0.5},
            {"standardized_interaction": -0.1},
            {"replicates": 0},
            {"alpha": 0.0},
            {"alpha": 1.0},
        ]
        for replacement in invalid:
            values = valid | replacement
            with self.subTest(replacement=replacement), self.assertRaises(DesignError):
                PowerScenario(**values).validate()

    def test_matrix_helpers_and_singular_fit(self) -> None:
        inverse = _invert_3x3([[2.0, 0.0, 0.0], [0.0, 4.0, 0.0], [0.0, 0.0, 5.0]])
        self.assertEqual(inverse, [[0.5, 0.0, 0.0], [0.0, 0.25, 0.0], [0.0, 0.0, 0.2]])
        with self.assertRaises(SingularDesignError):
            _invert_3x3([[1.0, 1.0, 1.0], [1.0, 1.0, 1.0], [1.0, 1.0, 1.0]])
        with self.assertRaises(SingularDesignError):
            _fit_interaction_hc3([1.0] * 8, [0.0] * 8, [1.0] * 8)

    def test_support_probability_and_critical_helpers(self) -> None:
        self.assertAlmostEqual(_effective_sample_size([1.0, 1.0, 0.0]), 2.0)
        self.assertEqual(_effective_sample_size([0.0, 0.0]), 0.0)
        self.assertAlmostEqual(_contrast_information([1.0, 0.0]), 0.5)
        posterior = _posterior_state_probability([1.0, 0.0], 0.2, 0.1)
        self.assertAlmostEqual(posterior[0], 0.18 / 0.26)
        self.assertAlmostEqual(posterior[1], 0.02 / 0.74)
        self.assertGreater(_t_critical_approx(0.05, 20), 1.96)
        self.assertNotEqual(_scenario_seed(5, (0, 0, 0, 0)), _scenario_seed(5, (0, 0, 0, 1)))

    def test_load_and_run_minimal_grid(self) -> None:
        raw = {
            "experiment_id": "test-grid",
            "evidence_status": "SYNTHETIC_DESIGN_ONLY",
            "seed": 1,
            "replicates": 2,
            "alpha": 0.05,
            "power_target": 0.8,
            "workers": 1,
            "sample_sizes": {"small": 20},
            "minority_prevalences": [0.25],
            "misclassification_rates": [0.1],
            "standardized_interactions": [0.0, 0.5],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "grid.yaml"
            path.write_text(yaml.safe_dump(raw), encoding="utf-8")
            grid = load_design_grid(path)
        payload = run_design_grid(grid)
        self.assertEqual(payload["experiment_id"], "test-grid")
        self.assertEqual(len(payload["results"]), 2)
        self.assertEqual(payload["results"][0]["sample_label"], "small")

    def test_load_grid_rejects_malformed_inputs(self) -> None:
        valid = {
            "experiment_id": "test-grid",
            "evidence_status": "SYNTHETIC_DESIGN_ONLY",
            "seed": 1,
            "replicates": 1,
            "alpha": 0.05,
            "power_target": 0.8,
            "sample_sizes": {"small": 20},
            "minority_prevalences": [0.25],
            "misclassification_rates": [0.1],
            "standardized_interactions": [0.5],
        }
        variants = [
            ["not", "a", "mapping"],
            valid | {"sample_sizes": {}},
            valid | {"sample_sizes": {"bad": True}},
            valid | {"experiment_id": ""},
            valid | {"evidence_status": "EMPIRICAL"},
            valid | {"replicates": 0},
            valid | {"alpha": 1.0},
            valid | {"power_target": 0.0},
            valid | {"workers": 0},
            valid | {"minority_prevalences": []},
            valid | {"minority_prevalences": ["bad"]},
            valid | {"misclassification_rates": [0.5]},
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "grid.yaml"
            for index, variant in enumerate(variants):
                with self.subTest(index=index):
                    path.write_text(yaml.safe_dump(variant), encoding="utf-8")
                    with self.assertRaises(DesignError):
                        load_design_grid(path)


if __name__ == "__main__":
    unittest.main()
