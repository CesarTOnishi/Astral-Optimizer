import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import enka
from PySide6.QtWidgets import QApplication

from app.api.enka_client import classify_account_error, ensure_account_error
from app.ui.error_recovery import EnkaErrorRecoveryPanel


class EnkaErrorClassificationTests(unittest.TestCase):
    def test_distinguishes_uid_rate_service_timeout_and_network(self) -> None:
        cases = (
            (enka.errors.WrongUIDFormatError(), "invalid_uid", False, False),
            (enka.errors.PlayerDoesNotExistError(), "uid_not_found", False, False),
            (enka.errors.RateLimitedError(), "rate_limited", True, False),
            (enka.errors.GameMaintenanceError(), "service_unavailable", True, False),
            (enka.errors.GatewayTimeoutError(), "service_unavailable", True, False),
            (enka.errors.APIRequestTimeoutError(), "timeout", True, True),
            (ConnectionError("offline"), "network", True, True),
        )
        for exception, code, retryable, check_connection in cases:
            with self.subTest(code=code, exception=type(exception).__name__):
                result = classify_account_error(exception)
                self.assertEqual(result.code, code)
                self.assertEqual(result.retryable, retryable)
                self.assertEqual(result.check_connection, check_connection)
                self.assertIn(type(exception).__name__, result.diagnostic_details)

    def test_legacy_message_is_converted_to_structured_error(self) -> None:
        result = ensure_account_error("falha antiga")
        self.assertEqual(result.code, "unknown")
        self.assertEqual(result.message, "falha antiga")


class EnkaErrorRecoveryPanelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_actions_match_error_and_cache_availability(self) -> None:
        panel = EnkaErrorRecoveryPanel()
        try:
            network = classify_account_error(ConnectionError("offline"))
            panel.show_error(network, has_saved_data=True)
            self.assertFalse(panel.retry_button.isHidden())
            self.assertFalse(panel.continue_button.isHidden())
            self.assertFalse(panel.connection_button.isHidden())
            self.assertFalse(panel.copy_button.isHidden())

            invalid = classify_account_error(enka.errors.WrongUIDFormatError())
            panel.show_error(invalid, has_saved_data=False)
            self.assertTrue(panel.retry_button.isHidden())
            self.assertTrue(panel.continue_button.isHidden())
            self.assertTrue(panel.connection_button.isHidden())
            self.assertFalse(panel.copy_button.isHidden())
        finally:
            panel.deleteLater()

    def test_copy_action_emits_structured_error(self) -> None:
        panel = EnkaErrorRecoveryPanel()
        received = []
        try:
            error = classify_account_error(enka.errors.RateLimitedError())
            panel.copy_requested.connect(received.append)
            panel.show_error(error, has_saved_data=False)
            panel.copy_button.click()
            self.assertEqual(received, [error])
        finally:
            panel.deleteLater()


if __name__ == "__main__":
    unittest.main()
