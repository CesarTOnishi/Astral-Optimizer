import os
import unittest
from unittest.mock import patch
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QPlainTextEdit

from app.performance import (
    PerformanceMetrics, diagnostic_lines, measured, process_memory_bytes,
)
from app.ui.experience import DiagnosticsPanel
from app.benchmark.fribbels_client import FribbelsBenchmarkWorker
from app.warp.importer import WarpImportWorker


class PerformanceTests(unittest.TestCase):
    def test_samples_are_aggregated_without_retaining_events(self) -> None:
        metrics = PerformanceMetrics()
        metrics.record("Planejador", 0.1)
        metrics.record("Planejador", 0.3)
        metrics.record("Outro", 5.0)
        sample = metrics.snapshot()["Planejador"]
        self.assertEqual(sample.count, 2)
        self.assertAlmostEqual(sample.last_ms, 300)
        self.assertAlmostEqual(sample.average_ms, 200)
        self.assertAlmostEqual(sample.minimum_ms, 100)
        self.assertAlmostEqual(sample.maximum_ms, 300)
        self.assertEqual(len(metrics.snapshot()), 1)

    def test_decorator_and_diagnostics_use_real_samples(self) -> None:
        metrics = PerformanceMetrics()
        with patch("app.performance.PERFORMANCE", metrics):
            @measured("Planejador")
            def calculate() -> int:
                return 42

            self.assertEqual(calculate(), 42)
        with patch("app.performance.process_memory_bytes", return_value=104857600):
            lines = diagnostic_lines(metrics)
        self.assertIn("Memória residente do processo: 100.0 MiB", lines)
        self.assertTrue(any("Planejador: último" in line for line in lines))
        self.assertTrue(any("Maior média observada: Planejador" in line for line in lines))
        self.assertTrue(any("Benchmark Fribbels: ainda não medido" in line for line in lines))

    def test_memory_is_available_on_supported_system(self) -> None:
        if os.name == "nt" or os.path.isfile("/proc/self/statm"):
            memory = process_memory_bytes()
            self.assertIsNotNone(memory)
            self.assertGreater(memory, 0)

    def test_background_workers_record_calculation_and_import(self) -> None:
        metrics = PerformanceMetrics()
        with patch("app.benchmark.fribbels_client.PERFORMANCE", metrics), patch(
            "app.benchmark.fribbels_client.calculate", return_value={}
        ):
            FribbelsBenchmarkWorker(object(), request_key="test").run()
        with patch("app.warp.importer.PERFORMANCE", metrics), patch(
            "app.warp.importer.import_starrailstation_xlsx", return_value=object()
        ):
            WarpImportWorker(Path("mock.xlsx"), "123").run()
        self.assertEqual(metrics.snapshot()["Benchmark Fribbels"].count, 1)
        self.assertEqual(metrics.snapshot()["Importação · leitura e rede"].count, 1)

    def test_diagnostics_field_scrolls_and_is_copyable(self) -> None:
        app = QApplication.instance() or QApplication([])
        panel = DiagnosticsPanel({})
        self.assertIsInstance(panel.summary, QPlainTextEdit)
        self.assertTrue(panel.summary.isReadOnly())
        self.assertIn("DESEMPENHO DESTA SESSÃO", panel.details)
        panel.copy_details()
        self.assertEqual(app.clipboard().text(), panel.details)
        panel.close()


if __name__ == "__main__":
    unittest.main()
