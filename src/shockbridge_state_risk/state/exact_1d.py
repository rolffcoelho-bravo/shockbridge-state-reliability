"""Deterministic globally optimal one-dimensional k-means clustering."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]


class Exact1DClusteringError(ValueError):
    """Raised when exact scalar clustering inputs cannot define the requested partition."""


@dataclass(frozen=True)
class Exact1DKMeansFit:
    labels: IntArray
    centers: FloatArray
    inertia: float
    boundaries: tuple[float, ...]


def _interval_inertia(
    prefix: FloatArray, prefix_squared: FloatArray, start: int, stop: int
) -> float:
    """Return within-cluster sum of squares for sorted values[start:stop]."""
    count = stop - start
    total = float(prefix[stop] - prefix[start])
    total_squared = float(prefix_squared[stop] - prefix_squared[start])
    return max(0.0, total_squared - total * total / count)


def fit_exact_1d_kmeans(values: FloatArray, n_clusters: int) -> Exact1DKMeansFit:
    """Minimize one-dimensional within-cluster sum of squares by dynamic programming."""
    array = np.asarray(values, dtype=np.float64)
    if array.ndim != 1 or array.size == 0:
        raise Exact1DClusteringError("Exact 1-D k-means requires a nonempty vector.")
    if np.any(~np.isfinite(array)):
        raise Exact1DClusteringError("Exact 1-D k-means requires finite values.")
    if n_clusters < 1 or n_clusters > array.size:
        raise Exact1DClusteringError("The cluster count must be between one and the sample size.")
    if np.unique(array).size < n_clusters:
        raise Exact1DClusteringError("The requested clusters require enough distinct values.")

    order = np.argsort(array, kind="stable")
    sorted_values = array[order]
    count = sorted_values.size
    centered_values = sorted_values - float(np.mean(sorted_values))
    prefix = np.concatenate((np.zeros(1), np.cumsum(centered_values)))
    prefix_squared = np.concatenate((np.zeros(1), np.cumsum(centered_values**2)))

    objective = np.full((n_clusters + 1, count + 1), np.inf, dtype=np.float64)
    split = np.full((n_clusters + 1, count + 1), -1, dtype=np.int64)
    objective[0, 0] = 0.0
    for clusters in range(1, n_clusters + 1):
        for stop in range(clusters, count + 1):
            best_value = np.inf
            best_start = -1
            for start in range(clusters - 1, stop):
                if not np.isfinite(objective[clusters - 1, start]):
                    continue
                candidate = objective[clusters - 1, start] + _interval_inertia(
                    prefix, prefix_squared, start, stop
                )
                if best_start < 0 or candidate < best_value:
                    best_value = candidate
                    best_start = start
            objective[clusters, stop] = best_value
            split[clusters, stop] = best_start

    sorted_labels = np.empty(count, dtype=np.int64)
    centers = np.empty(n_clusters, dtype=np.float64)
    stop = count
    for cluster in range(n_clusters - 1, -1, -1):
        start = int(split[cluster + 1, stop])
        if start < 0:
            raise Exact1DClusteringError("Exact clustering backtracking failed.")
        sorted_labels[start:stop] = cluster
        centers[cluster] = float(np.mean(sorted_values[start:stop]))
        stop = start
    labels = np.empty(count, dtype=np.int64)
    labels[order] = sorted_labels
    boundaries = tuple(
        float((centers[left] + centers[left + 1]) / 2.0) for left in range(n_clusters - 1)
    )
    inertia = float(objective[n_clusters, count])
    return Exact1DKMeansFit(labels, centers, inertia, boundaries)
