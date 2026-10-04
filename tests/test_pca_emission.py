import unittest

import numpy as np

from shockbridge_state_risk.state.pca_emission import (
    PCAEmissionError,
    predict_full_rank_pca_emission,
)


class FullRankPCAEmissionTests(unittest.TestCase):
    @staticmethod
    def _fixture(rows: int = 80) -> np.ndarray:
        index = np.arange(rows, dtype=np.float64)
        regime = np.where(index < rows / 2, -1.0, 1.0)
        values = np.column_stack(
            (
                0.8 * regime + 0.1 * np.sin(index),
                -1.2 * regime + 0.2 * np.cos(index / 3.0),
                1.1 * regime + 0.1 * np.sin(index / 4.0),
                0.4 * regime + 0.3 * np.cos(index / 5.0),
            )
        )
        values = (values - np.mean(values, axis=0)) / np.std(values, axis=0)
        values[7, 0] = np.nan
        values[12, 3] = np.nan
        return values

    def test_prediction_uses_coherent_full_rank_density(self) -> None:
        train = self._fixture()
        current = np.asarray([0.7, -0.9, 0.8, np.nan])
        prediction = predict_full_rank_pca_emission(train, current, 2, 2, 5, 0.05, 17)
        self.assertAlmostEqual(float(np.sum(prediction.probabilities)), 1.0)
        self.assertEqual(prediction.likelihood_dimensions_observed, 3)
        self.assertEqual(prediction.rotation.shape, (4, 4))
        self.assertEqual(prediction.raw_covariances.shape, (2, 4, 4))
        self.assertEqual(prediction.leading_cluster_centers.shape, (2, 2))
        self.assertEqual(sorted(np.unique(prediction.labels).tolist()), [0, 1])
        self.assertEqual(len(prediction.restart_records), 5)
        self.assertEqual(
            [record.seed for record in prediction.restart_records],
            [17 + restart * 1009 for restart in range(5)],
        )
        self.assertEqual(
            min(record.objective_gap_from_best for record in prediction.restart_records), 0.0
        )
        self.assertAlmostEqual(
            min(record.agreement_with_best for record in prediction.restart_records),
            prediction.restart_agreement,
        )
        self.assertTrue(
            all(
                len(record.aligned_hard_assignments) == len(train)
                for record in prediction.restart_records
            )
        )
        best_record = next(
            record for record in prediction.restart_records if record.objective_gap_from_best == 0.0
        )
        np.testing.assert_array_equal(best_record.aligned_hard_assignments, prediction.labels)
        for covariance in prediction.raw_covariances:
            np.testing.assert_allclose(covariance, covariance.T, atol=1e-12)
            self.assertTrue(np.all(np.linalg.eigvalsh(covariance) > 0.0))

        observed = np.isfinite(current)
        manual_components = []
        for state in range(2):
            mean = prediction.emission_means_pc[state] @ prediction.rotation
            covariance = prediction.raw_covariances[state][np.ix_(observed, observed)]
            difference = current[observed] - mean[observed]
            sign, log_determinant = np.linalg.slogdet(covariance)
            self.assertEqual(sign, 1.0)
            manual_components.append(
                np.log(prediction.mixture_weights[state])
                - 0.5
                * (
                    np.sum(observed) * np.log(2.0 * np.pi)
                    + log_determinant
                    + difference @ np.linalg.solve(covariance, difference)
                )
            )
        maximum = float(np.max(manual_components))
        expected = maximum + float(np.log(np.sum(np.exp(np.asarray(manual_components) - maximum))))
        self.assertAlmostEqual(prediction.log_predictive_score, expected)

    def test_prediction_is_deterministic_and_uses_only_supplied_history(self) -> None:
        train = self._fixture()
        current = np.asarray([0.7, -0.9, 0.8, 0.5])
        first = predict_full_rank_pca_emission(train, current, 2, 2, 4, 0.05, 9)
        second = predict_full_rank_pca_emission(train.copy(), current.copy(), 2, 2, 4, 0.05, 9)
        np.testing.assert_array_equal(first.probabilities, second.probabilities)
        np.testing.assert_array_equal(first.labels, second.labels)
        np.testing.assert_array_equal(first.raw_covariances, second.raw_covariances)
        self.assertEqual(first.log_predictive_score, second.log_predictive_score)
        self.assertEqual(first.model_definition, "LEADING_PC_CLUSTER_FULL_RANK_PC_EMISSION")

    def test_invalid_inputs_fail_closed(self) -> None:
        train = self._fixture()
        current = np.asarray([0.7, -0.9, 0.8, 0.5])
        cases = (
            (train[:3], current, 2, 2, 4, 0.05),
            (train, current[:3], 2, 2, 4, 0.05),
            (train, np.full(4, np.nan), 2, 2, 4, 0.05),
            (train, current, 1, 2, 4, 0.05),
            (train, current, 2, 0, 4, 0.05),
            (train, current, 2, 5, 4, 0.05),
            (train, current, 2, 2, 1, 0.05),
            (train, current, 2, 2, 4, 0.0),
            (train, current, 2, 2, 4, np.nan),
        )
        for historical, observation, states, components, restarts, floor in cases:
            with self.subTest(states=states, components=components, restarts=restarts, floor=floor):
                with self.assertRaises(PCAEmissionError):
                    predict_full_rank_pca_emission(
                        historical, observation, states, components, restarts, floor, 1
                    )

        invalid = train.copy()
        invalid[0, 0] = np.inf
        with self.assertRaisesRegex(PCAEmissionError, "infinities"):
            predict_full_rank_pca_emission(invalid, current, 2, 2, 4, 0.05, 1)


if __name__ == "__main__":
    unittest.main()
