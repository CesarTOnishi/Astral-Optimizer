from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from PySide6.QtCore import QSettings

from app.session_state import ResumeState, SessionStateStore


class SessionStateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = TemporaryDirectory()
        self.settings = QSettings(
            str(Path(self.directory.name) / "session.ini"),
            QSettings.Format.IniFormat,
        )
        self.settings.clear()
        self.store = SessionStateStore(self.settings)

    def tearDown(self) -> None:
        self.settings.clear()
        self.directory.cleanup()

    def test_round_trip_preserves_navigation_and_controls(self) -> None:
        expected = ResumeState(
            page="relics",
            uid="604955154",
            character_id="1221",
            values={
                "relics.character": "1221",
                "relics.status": "moved",
                "relics.sort": "score_asc",
                "catalog.search": "Acheron",
            },
            scrolls={"relics.v": 812, "builds.characters.h": 144},
        )

        self.store.save(7, expected)

        self.assertTrue(self.store.exists(7))
        self.assertEqual(self.store.load(7), expected)

    def test_state_is_isolated_between_local_profiles(self) -> None:
        self.store.save(1, ResumeState(page="warps", uid="600000001"))
        self.store.save(2, ResumeState(page="catalog", uid="600000002"))

        self.assertEqual(self.store.load(1).page, "warps")
        self.assertEqual(self.store.load(1).uid, "600000001")
        self.assertEqual(self.store.load(2).page, "catalog")
        self.assertEqual(self.store.load(2).uid, "600000002")
        self.assertEqual(self.store.load(0), ResumeState())

    def test_corrupt_or_invalid_data_uses_safe_defaults(self) -> None:
        self.settings.setValue("profiles/3/resume", "{not-json")
        self.assertEqual(self.store.load(3), ResumeState())

        self.settings.setValue(
            "profiles/4/resume",
            json.dumps(
                {
                    "page": ["invalid"],
                    "uid": "abc",
                    "character_id": 1221,
                    "values": {
                        "catalog.search": "ok", "number": 5, 2: "ignored"
                    },
                    "scrolls": {
                        "negative": -20,
                        "huge": 99_999_999,
                        "invalid": "no",
                        "boolean": True,
                    },
                }
            ),
        )

        restored = self.store.load(4)
        self.assertEqual(restored.page, "home")
        self.assertEqual(restored.uid, "")
        self.assertEqual(restored.character_id, "")
        self.assertEqual(restored.values, {"catalog.search": "ok"})
        self.assertEqual(
            restored.scrolls, {"negative": 0, "huge": 10_000_000}
        )


if __name__ == "__main__":
    unittest.main()
