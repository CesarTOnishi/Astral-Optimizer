import unittest

from app.warp.analytics import analyze_warps, detect_history_gaps
from app.warp.models import WarpRecord, WarpSummary


def record(index: int, rank: int = 3, banner: str = "v1") -> WarpRecord:
    return WarpRecord(
        str(index), "600000001", "11", "1003" if rank == 5 else "1",
        "Himeko" if rank == 5 else "Item", "Character", rank,
        f"2026-0{1 + index // 3}-01 00:00:00", "Versão 4.0", "Outra", banner,
    )


class WarpAnalyticsTests(unittest.TestCase):
    def test_groups_months_editions_and_outcomes(self) -> None:
        records = [record(0), record(1, 5), record(3), record(4, 5)]
        result = analyze_warps(records, {}, "11")
        self.assertEqual(result.monthly, (("2026-01", 2), ("2026-02", 2)))
        self.assertEqual(result.editions[0], ("Versão 4.0 · v1", 4))
        self.assertEqual(result.losses, 2)
        self.assertAlmostEqual(result.personal_average or 0, 2.0)

    def test_reports_summary_and_unidentified_records(self) -> None:
        item = record(0, banner="")
        summary = WarpSummary(item.uid, "11", 50, 1, 4, 20, 2, "", "", 30, "")
        gaps = detect_history_gaps([item], summary)
        titles = {gap.title for gap in gaps}
        self.assertIn("Edições não identificadas", titles)
        self.assertIn("Somente resumo disponível", titles)


if __name__ == "__main__":
    unittest.main()
