import itertools
import unittest

import numpy as np

from shockbridge_state_risk.state.exact_1d import (
    Exact1DClusteringError,
    fit_exact_1d_kmeans,
)


class Exact1DKMeansTests(unittest.TestCase):
    @staticmethod
    def _brute_force_inertia(values: np.ndarray, n_clusters: int) -> float:
        ordered = np.sort(values)
        best = np.inf
        for boundaries in itertools.combinations(range(1, len(ordered)), n_clusters - 1):
            starts = (0, *boundaries)
            stops = (*boundaries, len(ordered))
            inertia = sum(
                float(np.sum((ordered[start:stop] - np.mean(ordered[start:stop])) ** 2))
                for start, stop in zip(starts, stops)
            )
            best = min(best, inertia)
        return float(best)

    def test_matches_brute_force_optimum_and_is_order_invariant(self) -> None:
        values = np.asarray([4.2, -1.0, 0.1, 4.0, 9.0, 0.0, 8.7])
        fit = fit_exact_1d_kmeans(values, 3)
        self.assertAlmostEqual(fit.inertia, self._brute_force_inertia(values, 3))
        self.assertTrue(np.all(np.diff(fit.centers) > 0))
        self.assertEqual(len(fit.boundaries), 2)

        permutation = np.asarray([6, 1, 5, 3, 0, 4, 2])
        permuted = fit_exact_1d_kmeans(values[permutation], 3)
        restored_labels = np.empty_like(permuted.labels)
        restored_labels[permutation] = permuted.labels
        np.testing.assert_array_equal(restored_labels, fit.labels)
        np.testing.assert_allclose(permuted.centers, fit.centers)
        self.assertEqual(permuted.inertia, fit.inertia)

        translated = fit_exact_1d_kmeans(values + 1e9, 3)
        np.testing.assert_array_equal(translated.labels, fit.labels)
        np.testing.assert_allclose(translated.centers - 1e9, fit.centers, atol=1e-7)
        self.assertAlmostEqual(translated.inertia, fit.inertia, places=6)

    def test_single_cluster_and_invalid_inputs(self) -> None:
        fit = fit_exact_1d_kmeans(np.asarray([3.0, 1.0, 2.0]), 1)
        np.testing.assert_array_equal(fit.labels, np.zeros(3, dtype=np.int64))
        np.testing.assert_allclose(fit.centers, np.asarray([2.0]))
        self.assertAlmostEqual(fit.inertia, 2.0)

        invalid = (
            (np.asarray([]), 1),
            (np.asarray([[1.0, 2.0]]), 1),
            (np.asarray([1.0, np.nan]), 1),
            (np.asarray([1.0, 2.0]), 0),
            (np.asarray([1.0, 1.0, 2.0]), 3),
        )
        for values, clusters in invalid:
            with self.subTest(values=values, clusters=clusters):
                with self.assertRaises(Exact1DClusteringError):
                    fit_exact_1d_kmeans(values, clusters)


if __name__ == "__main__":
    unittest.main()
