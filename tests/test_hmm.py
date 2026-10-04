import unittest
from unittest.mock import patch

import numpy as np

from shockbridge_state_risk.state.hmm import (
    HMMError,
    HMMFit,
    HMMParameters,
    alignment_order,
    audit_hmm_restarts,
    diagonal_gaussian_log_score,
    filter_next,
    fit_diagonal_gaussian_hmm,
    fit_hmm_restarts,
    hmm_restart_gap_sensitivity,
    reorder_fit,
)


class HMMTests(unittest.TestCase):
    @staticmethod
    def _fixture() -> np.ndarray:
        # Deterministic numerical fixture for software validation only; never evidence.
        low = np.column_stack((np.linspace(-1.4, -0.6, 15), np.linspace(0.9, 1.4, 15)))
        high = np.column_stack((np.linspace(0.7, 1.5, 15), np.linspace(-1.3, -0.7, 15)))
        values = np.vstack((low, high, low[:8]))
        values[4, 0] = np.nan
        return values

    def test_fit_converges_after_more_than_one_iteration(self) -> None:
        values = self._fixture()
        fit = fit_diagonal_gaussian_hmm(values, max_iterations=150, seed=17)
        self.assertGreater(fit.iterations, 1)
        self.assertTrue(fit.converged)
        np.testing.assert_allclose(fit.filtered_probabilities.sum(axis=1), 1.0)
        self.assertTrue(np.isfinite(fit.log_likelihood))
        self.assertTrue(np.isfinite(fit.regularized_objective))

    def test_restart_selection_uses_regularized_map_objective(self) -> None:
        values = self._fixture()
        parameters = HMMParameters(
            initial=np.asarray([0.5, 0.5]),
            transition=np.asarray([[0.8, 0.2], [0.2, 0.8]]),
            means=np.zeros((2, 2)),
            variances=np.ones((2, 2)),
        )
        filtered = np.full((values.shape[0], 2), 0.5)
        raw_likelihood_winner = HMMFit(
            parameters=parameters,
            log_likelihood=12.0,
            regularized_objective=8.0,
            iterations=2,
            converged=True,
            seed=1,
            filtered_probabilities=filtered,
        )
        map_objective_winner = HMMFit(
            parameters=parameters,
            log_likelihood=11.0,
            regularized_objective=9.0,
            iterations=2,
            converged=True,
            seed=2,
            filtered_probabilities=filtered,
        )
        with patch(
            "shockbridge_state_risk.state.hmm.fit_diagonal_gaussian_hmm",
            side_effect=(raw_likelihood_winner, map_objective_winner),
        ):
            best, fits = fit_hmm_restarts(values, 2, 2, 10, 1e-6, 0.05, 0.5, 1)
        self.assertIs(best, map_objective_winner)
        self.assertEqual(fits, (raw_likelihood_winner, map_objective_winner))

    def test_restarts_alignment_and_one_step_filter(self) -> None:
        values = self._fixture()
        best, fits = fit_hmm_restarts(values, 2, 3, 100, 1e-6, 0.05, 0.5, 23)
        swapped = reorder_fit(best, (1, 0))
        self.assertEqual(alignment_order(best.parameters.means, swapped.parameters.means), (1, 0))
        posterior, score = filter_next(
            best.parameters,
            best.filtered_probabilities[-1],
            np.asarray([np.nan, 1.0]),
        )
        self.assertEqual(len(fits), 3)
        self.assertAlmostEqual(float(np.sum(posterior)), 1.0)
        self.assertTrue(np.isfinite(score))

    def test_restart_audit_retains_provenance(self) -> None:
        values = self._fixture()
        best, fits = fit_hmm_restarts(values, 2, 3, 100, 1e-6, 0.05, 0.5, 23)
        audit = audit_hmm_restarts(fits)
        self.assertEqual(audit.best_seed, best.seed)
        self.assertEqual(len(audit.records), 3)
        self.assertAlmostEqual(sum(record.objective_weight for record in audit.records), 1.0)
        self.assertGreaterEqual(audit.objective_weighted_agreement, 0.0)
        self.assertLessEqual(audit.objective_weighted_agreement, 1.0)
        self.assertGreaterEqual(audit.effective_restart_count, 1.0)
        self.assertLessEqual(audit.effective_restart_count, 3.0)
        self.assertEqual(min(record.objective_gap_from_best for record in audit.records), 0.0)
        self.assertTrue(
            all(len(record.aligned_hard_assignments) == len(values) for record in audit.records)
        )
        self.assertEqual(
            audit.diagnostic_weight_interpretation,
            "NUMERICAL_DIAGNOSTIC_NOT_POSTERIOR_PROBABILITY",
        )

    def test_restart_audit_downweights_a_poor_local_optimum(self) -> None:
        parameters = HMMParameters(
            initial=np.asarray([0.5, 0.5]),
            transition=np.asarray([[0.8, 0.2], [0.2, 0.8]]),
            means=np.asarray([[-1.0, 1.0], [1.0, -1.0]]),
            variances=np.ones((2, 2)),
        )
        best_filtered = np.vstack((np.tile([0.99, 0.01], (5, 1)), np.tile([0.01, 0.99], (5, 1))))
        poor_filtered = np.asarray(
            [[0.99, 0.01] if index % 2 == 0 else [0.01, 0.99] for index in range(10)]
        )
        best = HMMFit(parameters, -10.0, -12.0, 5, True, 1, best_filtered)
        poor = HMMFit(parameters, -59.0, -62.0, 5, True, 2, poor_filtered)
        audit = audit_hmm_restarts((best, poor))
        self.assertAlmostEqual(audit.minimum_all_start_agreement, 0.6)
        self.assertGreater(audit.objective_weighted_agreement, 0.999999)
        self.assertAlmostEqual(audit.records[1].objective_gap_from_best, 50.0)
        self.assertEqual(
            audit.records[1].aligned_hard_assignments, tuple(np.argmax(poor_filtered, axis=1))
        )
        self.assertLess(audit.records[1].objective_weight, 1e-20)
        self.assertAlmostEqual(audit.effective_restart_count, 1.0)

        sensitivity = hmm_restart_gap_sensitivity(audit, (0.0, 2.0, 10.0, 50.0))
        self.assertEqual([item.included_restarts for item in sensitivity], [1, 1, 1, 2])
        self.assertEqual(sensitivity[0].minimum_agreement, 1.0)
        self.assertEqual(sensitivity[-1].minimum_agreement, 0.6)
        self.assertGreater(sensitivity[-1].objective_weighted_agreement, 0.999999)

    def test_restart_gap_sensitivity_rejects_invalid_grids(self) -> None:
        _, fits = fit_hmm_restarts(self._fixture(), 2, 2, 100, 1e-6, 0.05, 0.5, 23)
        audit = audit_hmm_restarts(fits)
        for grid in ((), (-1.0,), (0.0, 0.0), (2.0, 1.0), (np.nan,)):
            with self.subTest(grid=grid):
                with self.assertRaises(HMMError):
                    hmm_restart_gap_sensitivity(audit, grid)

    def test_restart_audit_rejects_empty_or_nonfinite_objectives(self) -> None:
        with self.assertRaises(HMMError):
            audit_hmm_restarts(())
        fit = fit_diagonal_gaussian_hmm(self._fixture(), max_iterations=100, seed=4)
        invalid = HMMFit(
            parameters=fit.parameters,
            log_likelihood=fit.log_likelihood,
            regularized_objective=np.nan,
            iterations=fit.iterations,
            converged=fit.converged,
            seed=fit.seed,
            filtered_probabilities=fit.filtered_probabilities,
        )
        with self.assertRaisesRegex(HMMError, "finite"):
            audit_hmm_restarts((invalid,))

        malformed = HMMFit(
            parameters=fit.parameters,
            log_likelihood=fit.log_likelihood,
            regularized_objective=fit.regularized_objective,
            iterations=fit.iterations,
            converged=fit.converged,
            seed=fit.seed,
            filtered_probabilities=fit.filtered_probabilities[:-1],
        )
        with self.assertRaisesRegex(HMMError, "same filtered-probability shape"):
            audit_hmm_restarts((fit, malformed))

    def test_initialization_falls_back_for_cluster_local_missing_feature(self) -> None:
        values = self._fixture()
        values[:15, 0] = np.nan
        fit = fit_diagonal_gaussian_hmm(values, max_iterations=100, seed=17)
        self.assertTrue(np.all(np.isfinite(fit.parameters.means)))
        self.assertTrue(np.all(np.isfinite(fit.parameters.variances)))
        self.assertTrue(np.isfinite(fit.log_likelihood))

    def test_state_independent_score_and_invalid_inputs(self) -> None:
        values = self._fixture()
        score = diagonal_gaussian_log_score(values, np.asarray([0.0, np.nan]))
        self.assertTrue(np.isfinite(score))
        self.assertEqual(diagonal_gaussian_log_score(values, np.asarray([np.nan, np.nan])), 0.0)
        with self.assertRaises(HMMError):
            fit_diagonal_gaussian_hmm(np.ones((3, 2)))
        with self.assertRaises(HMMError):
            fit_hmm_restarts(values, 2, 0, 10, 1e-6, 0.05, 0.5, 1)
        values[0, 0] = np.inf
        with self.assertRaisesRegex(HMMError, "infinite"):
            fit_diagonal_gaussian_hmm(values)


if __name__ == "__main__":
    unittest.main()
