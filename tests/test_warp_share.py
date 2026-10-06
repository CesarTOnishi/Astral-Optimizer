from __future__ import annotations

import os
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.ui.warp_share import (
    CARD_SIZE,
    RESULTS_PER_PAGE,
    build_warp_share_data,
    pity_color,
    render_warp_share_card,
    render_warp_share_pages,
    warp_share_page_paths,
)
from app.warp.models import WarpRecord, WarpSummary


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

    def test_edition_export_uses_edition_totals_and_period(self) -> None:
        records = _sample_history()
        records[:28] = [replace(record, banner_id="banner-b") for record in records[:28]]
        summary = WarpSummary(
            uid="600123456", gacha_type="11", total=1418,
            five_star_count=2, four_star_count=0,
            five_star_pity=12, four_star_pity=0,
            featured_item_id="", featured_item_name="",
            featured_pity=0, featured_item_type="",
        )
        category = build_warp_share_data(
            records, {"11": summary}, "11", "Evento de Personagem", 90
        )
        edition = build_warp_share_data(
            records, {"11": summary}, "11", "Evento de Personagem", 90,
            edition_id="banner-b", edition_title="Banner da Pearl",
        )

        self.assertEqual(category.total, 1418)
        self.assertFalse(category.edition_filtered)
        self.assertEqual(edition.total, 28)
        self.assertTrue(edition.edition_filtered)
        self.assertEqual(edition.period, "2026-01-01 a 2026-01-01")
        self.assertEqual([result.record.id for result in edition.recent], ["20"])

        from app.ui.warp_share import _text
        labels: list[str] = []
        def capture(painter, rect, value, size, *args, **kwargs):
            labels.append(value)
            _text(painter, rect, value, size, *args, **kwargs)
        with patch("app.ui.warp_share._text", side_effect=capture):
            render_warp_share_pages(edition)
        self.assertIn("SALTOS NA EDIÇÃO", labels)
        self.assertIn("28", labels)
        self.assertIn("4.480", labels)
        self.assertNotIn("1.418", labels)

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

    def test_private_export_masks_uid_and_labels_jades_as_equivalent(self) -> None:
        data = build_warp_share_data(
            _sample_history(), {}, "11", "Evento de Personagem", 90
        )
        from app.ui.warp_share import _text
        labels: list[str] = []
        def capture(painter, rect, value, size, *args, **kwargs):
            labels.append(value)
            _text(painter, rect, value, size, *args, **kwargs)
        with patch("app.ui.warp_share._text", side_effect=capture):
            render_warp_share_pages(data, hide_uid=True)

        self.assertIn("UID •••••••••", labels)
        self.assertNotIn(f"UID {data.uid}", labels)
        self.assertIn("JADES EQUIVALENTES", labels)

    def test_extra_results_create_numbered_pages_without_dropping_records(self) -> None:
        data = build_warp_share_data(
            _sample_history(), {}, "11", "Evento de Personagem", 90
        )
        expanded = replace(data, recent=data.recent * 31)
        drawn: list[str] = []
        from app.ui.warp_share import _result_card
        def capture(painter, result, rect, cap, portraits):
            drawn.append(result.record.id)
            _result_card(painter, result, rect, cap, portraits)
        with patch("app.ui.warp_share._result_card", side_effect=capture):
            pages = render_warp_share_pages(expanded)

        self.assertEqual(RESULTS_PER_PAGE, 60)
        self.assertEqual(len(pages), 2)
        self.assertTrue(all(page.width() == CARD_SIZE[0] and page.height() > CARD_SIZE[1] for page in pages))
        self.assertEqual(drawn, [result.record.id for result in expanded.recent])
        self.assertEqual(
            warp_share_page_paths(Path("Saltos.png"), len(pages)),
            (Path("Saltos_01.png"), Path("Saltos_02.png")),
        )

    def test_twenty_four_results_fit_three_by_eight_compact_image(self) -> None:
        data = build_warp_share_data(
            _sample_history(), {}, "11", "Evento de Personagem", 90
        )
        example = replace(data, recent=data.recent * 12)
        from app.ui.warp_share import _result_card
        positions: list[tuple[int, int]] = []
        def capture(painter, result, rect, cap, portraits):
            positions.append((int(rect.x()), int(rect.y())))
            _result_card(painter, result, rect, cap, portraits)
        with patch("app.ui.warp_share._result_card", side_effect=capture):
            pages = render_warp_share_pages(example)

        self.assertEqual(len(pages), 1)
        self.assertEqual((pages[0].width(), pages[0].height()), (1600, 1170))
        self.assertEqual(len({x for x, _y in positions}), 3)
        self.assertEqual(len({y for _x, y in positions}), 8)
        self.assertEqual(warp_share_page_paths(Path("Saltos.png"), 1), (Path("Saltos.png"),))


if __name__ == "__main__":
    unittest.main()
