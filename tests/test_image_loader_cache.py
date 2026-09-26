import os
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import QApplication

from app.ui.image_loader import ImageLoader


class ImageLoaderCacheTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_least_recent_images_leave_memory_without_losing_visible_pixmap(self) -> None:
        with TemporaryDirectory() as directory, patch.dict(
            os.environ, {"ASTRAL_DATA_DIR": directory}
        ):
            loader = ImageLoader()
            loader.MAX_MEMORY_IMAGES = 2
            loader.MAX_MEMORY_BYTES = 128
            pixmap = QPixmap(4, 4)
            pixmap.fill(QColor("#ffffff"))
            loader._remember("a", pixmap)
            loader._remember("b", pixmap)
            visible = []
            loader.load("a", visible.append)
            loader._remember("c", pixmap)

            self.assertEqual(list(loader.cache), ["a", "c"])
            self.assertNotIn("b", loader.cache)
            self.assertFalse(visible[0].isNull())
            self.assertLessEqual(loader._cache_bytes, loader.MAX_MEMORY_BYTES)

            loader.MAX_MEMORY_BYTES = 64
            loader._remember("d", pixmap)
            self.assertEqual(list(loader.cache), ["d"])
            self.assertLessEqual(loader._cache_bytes, 64)

    def test_oversized_image_is_not_held_in_memory(self) -> None:
        with TemporaryDirectory() as directory, patch.dict(
            os.environ, {"ASTRAL_DATA_DIR": directory}
        ):
            loader = ImageLoader()
            loader.MAX_MEMORY_BYTES = 8
            pixmap = QPixmap(4, 4)
            pixmap.fill(QColor("#ffffff"))
            loader._remember("large", pixmap)
            self.assertEqual(len(loader.cache), 0)
            self.assertEqual(loader._cache_bytes, 0)


if __name__ == "__main__":
    unittest.main()
