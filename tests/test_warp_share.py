from __future__ import annotations

import os
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.ui.warp_share import (
    CARD_SIZE,
    build_warp_share_data,
    pity_color,
    render_warp_share_card,
)
from app.warp.models import WarpRecord


def _record(
    identifier: int,
    *,
    rank: int = 3,
    item_id: str = "20000",
    name: str = "Item",
    featured: str = "",
    banner_id: str = "banner-a",
) -> WarpRecord:
    return WarpRecord(
        id=str(identifier),
        uid="600123456",
        gacha_type="11",
        item_id=item_id,
        name=name,
        item_type="Personagem" if rank == 5 else "Cone de Luz",
        rank_type=rank,
        time=f"2026-0{1 + (identifier - 1) // 28}-01 12:00:00",
        banner_title="Teste Astral",
        featured_name=featured,
        banner_id=banner_id,
    )


def _sample_history() -> list[WarpRecord]:
    records = [_record(index) for index in range(1, 21)]
    records[-1] = _record(
        20,
        rank=5,
        item_id="1003",
        name="Himeko",
        featured="Castorice",
    )
    records.extend(_record(index) for index in range(21, 51))
    records[-1] = _record(
        50,
        rank=5,
        item_id="1407",
        name="Castorice",
        featured="Castorice",
    )
    records.extend(_record(index) for index in range(51, 63))
    return records


class WarpShareTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setProperty("astralTheme", "astral")

    def test_build_data_includes_statistics_and_guarantee_history(self) -> None:
        data = build_warp_share_data(
            _sample_history(), {}, "11", "Evento de Personagem", 90
        )

        self.assertEqual(data.total, 62)
        self.assertEqual(data.five_star_count, 2)
        self.assertEqual(data.five_star_pity, 12)
        self.assertEqual(data.average_pity, 25.0)
        self.assertEqual(data.best_pity, 20)
        self.assertEqual(data.worst_pity, 30)
        self.assertEqual(data.losses, 1)
        self.assertEqual(data.guaranteed_results, 1)
        self.assertEqual(data.wins, 0)
        self.assertEqual(
            [result.outcome for result in data.recent], ["guaranteed", "lost"]
        )
        self.assertEqual(data.low_pity_count, 2)
        self.assertEqual(data.medium_pity_count, 0)
        self.assertEqual(data.high_pity_count, 0)

    def test_pity_colors_follow_low_medium_and_high_ranges(self) -> None:
        self.assertEqual(pity_color(60, 90), "#70e0a3")
        self.assertEqual(pity_color(61, 90), "#ffb45c")
        self.assertEqual(pity_color(76, 90), "#ff6f7d")

    def test_render_creates_png_with_privacy_enabled(self) -> None:
        data = build_warp_share_data(
            _sample_history(), {}, "11", "Evento de Personagem", 90
        )
        card = render_warp_share_card(data, hide_uid=True)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "saltos.png"
            self.assertEqual((card.width(), card.height()), CARD_SIZE)
            self.assertTrue(card.save(str(output), "PNG"))
            self.assertGreater(output.stat().st_size, 10_000)

    def test_card_grows_to_show_every_filtered_five_star(self) -> None:
        data = build_warp_share_data(
            _sample_history(), {}, "11", "Evento de Personagem", 90
        )
        expanded = replace(data, recent=data.recent * 13)
        card = render_warp_share_card(expanded)

        self.assertEqual(card.width(), CARD_SIZE[0])
        self.assertGreater(card.height(), CARD_SIZE[1])


if __name__ == "__main__":
    unittest.main()
