import unittest

from app.planner import calculate_planner, parse_goal_sequence, sequence_projections


class PlannerTests(unittest.TestCase):
    def test_custom_sequence_builds_optimistic_average_and_pessimistic_scenarios(self) -> None:
        self.assertEqual(parse_goal_sequence("E0 > S1 > E1"), ("E0", "S1", "E1"))
        results = sequence_projections("E0 > S1 > E1", 300, 0, False, 0, False)
        self.assertEqual([item.label for item in results], ["E0", "S1", "E1"])
        self.assertTrue(all(
            item.optimistic_warps <= item.expected_warps <= item.pessimistic_warps
            for item in results
        ))
        self.assertGreater(results[0].chance, results[-1].chance)

    def test_rejects_repeated_or_reversed_sequence_goals(self) -> None:
        with self.assertRaises(ValueError):
            parse_goal_sequence("E1 > E0")

    def test_converts_resources_and_applies_fribbels_average_refund(self) -> None:
        result = calculate_planner(
            jades=1600,
            passes=5,
            starlight=40,
            refund="average",
            character_pity=0,
            character_guaranteed=False,
            light_cone_pity=0,
            light_cone_guaranteed=False,
        )
        self.assertEqual(result.jade_warps, 10)
        self.assertEqual(result.starlight_warps, 2)
        self.assertEqual(result.refunded_warps, 1)
        self.assertEqual(result.total_warps, 18)

    def test_matches_fribbels_pity_reference_for_guaranteed_targets(self) -> None:
        result = calculate_planner(
            jades=0,
            passes=200,
            starlight=0,
            refund="none",
            character_pity=50,
            character_guaranteed=True,
            light_cone_pity=50,
            light_cone_guaranteed=True,
        )
        self.assertAlmostEqual(result.character.expected_warps, 25.66, places=1)
        self.assertAlmostEqual(result.light_cone.expected_warps, 18.03, places=1)
        self.assertEqual(result.character.worst_case, 40)
        self.assertEqual(result.light_cone.worst_case, 30)

    def test_zero_resources_have_zero_success_probability(self) -> None:
        result = calculate_planner(
            jades=0,
            passes=0,
            starlight=0,
            refund="none",
            character_pity=70,
            character_guaranteed=False,
            light_cone_pity=60,
            light_cone_guaranteed=False,
        )
        self.assertEqual(result.character.chance, 0)
        self.assertEqual(result.light_cone.chance, 0)

    def test_milestones_match_fribbels_e2_first_reference(self) -> None:
        result = calculate_planner(
            jades=0,
            passes=350,
            starlight=0,
            refund="average",
            character_pity=59,
            character_guaranteed=False,
            light_cone_pity=3,
            light_cone_guaranteed=False,
            strategy="E2",
        )

        self.assertEqual(result.total_warps, 376)
        self.assertEqual(
            [milestone.label for milestone in result.milestones[:4]],
            ["E0 S0", "E1 S0", "E2 S0", "E2 S1"],
        )
        self.assertAlmostEqual(result.milestones[2].chance, 0.982, places=3)
        self.assertAlmostEqual(result.milestones[3].chance, 0.862, places=3)
        self.assertEqual(
            [round(milestone.expected_warps) for milestone in result.milestones[:4]],
            [45, 135, 224, 288],
        )


if __name__ == "__main__":
    unittest.main()
