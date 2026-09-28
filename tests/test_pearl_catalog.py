from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from app.benchmark.catalog import load_catalog
from app.catalog.repository import CatalogRepository


class PearlCatalogTests(unittest.TestCase):
    def test_pearl_is_available_without_synchronized_catalog(self) -> None:
        with TemporaryDirectory() as directory:
            characters = CatalogRepository(Path(directory)).characters()
        pearl = next(item for item in characters if item.id == "1503")
        self.assertEqual((pearl.name, pearl.rarity, pearl.path, pearl.element),
                         ("Pearl", 5, "Elation", "Ice"))
        self.assertIn("1503", {item.id for item in load_catalog()[0]})
        with TemporaryDirectory() as directory:
            cones = CatalogRepository(Path(directory)).light_cones()
        self.assertIn("23055", {item.id for item in cones})
        self.assertIn("23055", {item.id for item in load_catalog()[1]})


if __name__ == "__main__":
    unittest.main()
