from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import zipfile

from app.updater import UpdateError, _payload_root, _safe_extract, is_newer_version


class UpdaterTests(unittest.TestCase):
    def test_semantic_version_comparison(self) -> None:
        self.assertTrue(is_newer_version("v1.1.0", "1.0.9"))
        self.assertFalse(is_newer_version("v1.0.0", "1.0"))
        self.assertFalse(is_newer_version("invalid", "1.0.0"))

    def test_payload_root_accepts_single_distribution_folder(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            payload = root / "AstralOptimizer"
            payload.mkdir()
            (payload / "AstralOptimizer.exe").touch()
            self.assertEqual(_payload_root(root), payload)

    def test_safe_extract_rejects_parent_traversal(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "bad.zip"
            with zipfile.ZipFile(archive, "w") as bundle:
                bundle.writestr("../outside.txt", "danger")
            with self.assertRaises(UpdateError):
                _safe_extract(archive, root / "output")


if __name__ == "__main__":
    unittest.main()
