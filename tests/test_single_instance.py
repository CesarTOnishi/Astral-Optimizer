import os
import subprocess
import sys
import time
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from uuid import uuid4

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.single_instance import SingleInstance, server_name


class SingleInstanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.directory = TemporaryDirectory()
        self.environment = patch.dict(
            os.environ, {"ASTRAL_DATA_DIR": self.directory.name}
        )
        self.environment.start()
        self.addCleanup(self.directory.cleanup)
        self.addCleanup(self.environment.stop)

    def _wait_for_activation(self, primary: SingleInstance, count: list[int]) -> None:
        deadline = time.monotonic() + 2
        while not count and time.monotonic() < deadline:
            self.app.processEvents()
            time.sleep(0.01)

    def test_second_coordinator_activates_first_and_server_can_restart(self) -> None:
        name = f"AstralOptimizer-test-{uuid4().hex}"
        primary = SingleInstance(name)
        secondary = SingleInstance(name)
        count: list[int] = []
        primary.activation_requested.connect(lambda: count.append(1))
        try:
            self.assertTrue(primary.start_or_activate())
            with patch.object(secondary, "_notify_existing", return_value=True) as notify:
                self.assertFalse(secondary.start_or_activate())
            notify.assert_called_once()
            self.assertIsNone(secondary.server)
        finally:
            primary.close()
            secondary.close()

        replacement = SingleInstance(name)
        try:
            self.assertTrue(replacement.start_or_activate())
        finally:
            replacement.close()

    def test_new_process_notifies_existing_process(self) -> None:
        name = f"AstralOptimizer-test-{uuid4().hex}"
        primary = SingleInstance(name)
        count: list[int] = []
        primary.activation_requested.connect(lambda: count.append(1))
        try:
            self.assertTrue(primary.start_or_activate())
            script = (
                "import sys; from PySide6.QtCore import QCoreApplication; "
                "from app.single_instance import SingleInstance; "
                "app = QCoreApplication([]); "
                "raise SystemExit(0 if not SingleInstance(sys.argv[1], app).start_or_activate() else 7)"
            )
            child = subprocess.Popen(
                [sys.executable, "-c", script, name],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            )
            self._wait_for_activation(primary, count)
            _stdout, stderr = child.communicate(timeout=10)
            self.assertEqual(child.returncode, 0, stderr)
            self.assertEqual(count, [1])
        finally:
            primary.close()

    def test_busy_instance_never_allows_a_second_listener(self) -> None:
        name = f"AstralOptimizer-test-{uuid4().hex}"
        primary = SingleInstance(name)
        secondary = SingleInstance(name)
        try:
            self.assertTrue(primary.start_or_activate())
            with patch.object(secondary, "_notify_existing", return_value=False), patch(
                "app.single_instance.time.sleep"
            ):
                with self.assertRaisesRegex(RuntimeError, "já está aberto"):
                    secondary.start_or_activate()
            self.assertIsNone(secondary.server)
        finally:
            secondary.close()
            primary.close()

    def test_crashed_process_does_not_leave_a_permanent_lock(self) -> None:
        name = f"AstralOptimizer-test-{uuid4().hex}"
        script = (
            "import os, sys; from PySide6.QtCore import QCoreApplication; "
            "from app.single_instance import SingleInstance; "
            "app = QCoreApplication([]); "
            "instance = SingleInstance(sys.argv[1], app); "
            "os._exit(0 if instance.start_or_activate() else 7)"
        )
        completed = subprocess.run(
            [sys.executable, "-c", script, name],
            capture_output=True, text=True, timeout=10, check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        replacement = SingleInstance(name)
        try:
            self.assertTrue(replacement.start_or_activate())
        finally:
            replacement.close()

    def test_name_is_stable_for_the_data_directory(self) -> None:
        with TemporaryDirectory() as directory:
            previous = os.environ.get("ASTRAL_DATA_DIR")
            os.environ["ASTRAL_DATA_DIR"] = directory
            try:
                self.assertEqual(server_name(), server_name())
                self.assertLess(len(server_name()), 50)
            finally:
                if previous is None:
                    del os.environ["ASTRAL_DATA_DIR"]
                else:
                    os.environ["ASTRAL_DATA_DIR"] = previous


if __name__ == "__main__":
    unittest.main()
