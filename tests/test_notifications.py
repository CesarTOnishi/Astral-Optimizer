import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.catalog.sync import local_catalog_commit
from app.ui.notifications import NotificationCenter


class NotificationCenterTests(unittest.TestCase):
    def test_deduplicates_updates_and_tracks_unread_items(self) -> None:
        center = NotificationCenter()
        center.add("backup", "Backup concluído", "Primeiro", "success")
        center.add("backup", "Erro no backup", "Segundo", "error")

        self.assertEqual(len(center.items), 1)
        self.assertEqual(center.items[0].title, "Erro no backup")
        self.assertEqual(center.unread_count, 1)

        center.mark_all_read()
        self.assertEqual(center.unread_count, 0)

        center.remove("backup")
        self.assertEqual(center.items, ())

    def test_reads_catalog_commit_from_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory)
            (cache / "metadata.json").write_text(
                json.dumps({"commit": "a" * 40}), encoding="utf-8"
            )
            with patch("app.catalog.sync.catalog_cache_dir", return_value=cache):
                self.assertEqual(local_catalog_commit(), "a" * 40)


if __name__ == "__main__":
    unittest.main()
