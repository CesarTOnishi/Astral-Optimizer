from __future__ import annotations

import os
from types import SimpleNamespace
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.section_loading import SectionLoadController
from app.api.enka_client import EnkaClient
from app.ui.section_loading import SectionStatus


class SectionLoadControllerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_sections_can_finish_independently(self) -> None:
        controller = SectionLoadController()
        context = controller.begin_context(4, "600000001")
        controller.pending("profile", "Carregando perfil", context)
        controller.pending("characters", "Carregando personagens", context)

        self.assertTrue(controller.ready("profile", context))
        self.assertEqual(controller.states["profile"].status, "ready")
        self.assertEqual(controller.states["characters"].status, "pending")

    def test_section_failure_can_retry_without_resetting_ready_sections(self) -> None:
        controller = SectionLoadController()
        context = controller.begin_context(4, "600000001")
        controller.ready("profile", context)
        controller.fail(
            "art", "Imagem indisponível", details="timeout", context=context
        )
        retries = []
        controller.retry_requested.connect(
            lambda section, current: retries.append((section, current))
        )

        controller.request_retry("art")

        self.assertEqual(retries, [("art", context)])
        self.assertEqual(controller.states["profile"].status, "ready")

    def test_old_results_are_ignored_after_account_or_profile_change(self) -> None:
        controller = SectionLoadController()
        old = controller.begin_context(4, "600000001")
        controller.pending("characters", "Carregando", old)
        current = controller.begin_context(9, "600000002")
        controller.pending("characters", "Nova conta", current)

        self.assertFalse(controller.ready("characters", old))
        self.assertEqual(controller.context, current)
        self.assertEqual(controller.states["characters"].message, "Nova conta")

    def test_reduced_motion_keeps_pending_indicator_static(self) -> None:
        self.app.setProperty("astralReduceMotion", True)
        status = SectionStatus("art")
        controller = SectionLoadController()
        context = controller.begin_context(0, "600000001")
        controller.pending("art", "Carregando", context)
        status.set_state(controller.states["art"])

        self.assertFalse(status.timer.isActive())
        self.assertEqual(status.height(), 28)
        status.deleteLater()
        self.app.setProperty("astralReduceMotion", False)

    def test_newer_same_uid_request_suppresses_previous_response(self) -> None:
        client = EnkaClient()
        received = []
        client.account_loaded.connect(lambda account, message: received.append(account))
        client.pending_request = ("600000001", True)

        client._account_ready("600000001", SimpleNamespace(ttl=60))

        self.assertEqual(received, [])
        client.deleteLater()


if __name__ == "__main__":
    unittest.main()
