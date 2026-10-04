import unittest
from dataclasses import replace

import numpy as np

from shockbridge_state_risk.transmission.bootstrap import (
    BootstrapError,
    evaluate_nested_bootstrap,
    make_circular_moving_block_plan,
)


class NestedBootstrapTests(unittest.TestCase):
    def test_plan_is_deterministic_and_preserves_within_block_order(self) -> None:
        first = make_circular_moving_block_plan(20, 4, 5, 19)
        second = make_circular_moving_block_plan(20, 4, 5, 19)
        self.assertEqual(first, second)
        self.assertEqual(first.first_stage_requirement, "REFIT_STATE_MODEL_INSIDE_EVERY_REPLICATE")
        for draw in first.draws:
            self.assertEqual(len(draw.observation_indices), 20)
            for block in range(5):
                segment = draw.observation_indices[block * 4 : (block + 1) * 4]
                expected = tuple((segment[0] + offset) % 20 for offset in range(4))
                self.assertEqual(segment, expected)

    def test_nested_callback_is_invoked_once_per_draw(self) -> None:
        plan = make_circular_moving_block_plan(20, 5, 7, 4)
        invocations: list[tuple[int, ...]] = []

        def refit(indices: np.ndarray) -> np.ndarray:
            invocations.append(tuple(int(value) for value in indices))
            return np.asarray([np.mean(indices), np.std(indices)])

        result = evaluate_nested_bootstrap(plan, refit)
        self.assertEqual(len(invocations), 7)
        self.assertEqual(result.estimates.shape, (7, 2))
        self.assertTrue(np.all(np.isfinite(result.estimates)))
        self.assertEqual(
            result.estimator_contract,
            "CALLBACK_REFITS_FIRST_STAGE_AND_TRANSMISSION_MODEL",
        )

    def test_invalid_bootstrap_contracts_fail_closed(self) -> None:
        for arguments in ((3, 2, 5, 1), (20, 1, 5, 1), (20, 21, 5, 1), (20, 4, 0, 1)):
            with self.subTest(arguments=arguments):
                with self.assertRaises(BootstrapError):
                    make_circular_moving_block_plan(*arguments)
        plan = make_circular_moving_block_plan(20, 4, 2, 1)
        with self.assertRaisesRegex(BootstrapError, "finite nonempty"):
            evaluate_nested_bootstrap(plan, lambda _: np.asarray([np.nan]))
        with self.assertRaisesRegex(BootstrapError, "replication count"):
            evaluate_nested_bootstrap(replace(plan, replications=3), lambda _: np.ones(1))


if __name__ == "__main__":
    unittest.main()
