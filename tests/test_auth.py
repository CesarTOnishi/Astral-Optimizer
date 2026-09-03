from pathlib import Path
import tempfile
import unittest

from PySide6.QtCore import QSettings

from app.auth import AuthService


class AuthTests(unittest.TestCase):
    def test_register_login_session_and_logout(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            settings = QSettings(str(root / "settings.ini"), QSettings.Format.IniFormat)
            service = AuthService(root / "accounts.db", settings)
            user = service.register("Trailblazer", "trailblazer@example.com", "senha-segura")
            self.assertEqual(user.username, "Trailblazer")
            self.assertEqual(service.login("trailblazer", "senha-segura"), user)
            self.assertEqual(service.login("TRAILBLAZER@example.com", "senha-segura"), user)
            user = service.update_game_uid("600000001")
            self.assertEqual(user.game_uid, "600000001")

            restored = AuthService(root / "accounts.db", settings)
            self.assertEqual(restored.current_user, user)
            restored.logout()
            self.assertIsNone(restored.current_user)

    def test_rejects_duplicate_and_wrong_password(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            settings = QSettings(str(root / "settings.ini"), QSettings.Format.IniFormat)
            service = AuthService(root / "accounts.db", settings)
            service.register("March7", "march7@example.com", "pom-pom-123")
            with self.assertRaisesRegex(ValueError, "já está cadastrado"):
                service.register("march7", "outro@example.com", "outra-senha")
            with self.assertRaisesRegex(ValueError, "e-mail já está cadastrado"):
                service.register("March8", "MARCH7@example.com", "outra-senha")
            with self.assertRaisesRegex(ValueError, "incorretos"):
                service.login("March7", "senha-errada")
            service.logout()

    def test_rejects_invalid_email(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            settings = QSettings(str(root / "settings.ini"), QSettings.Format.IniFormat)
            service = AuthService(root / "accounts.db", settings)
            with self.assertRaisesRegex(ValueError, "e-mail válido"):
                service.register("PomPom", "email-invalido", "expresso-123")

    def test_rejects_invalid_game_uid(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            settings = QSettings(str(root / "settings.ini"), QSettings.Format.IniFormat)
            service = AuthService(root / "accounts.db", settings)
            service.register("Himeko", "himeko@example.com", "expresso-123")
            with self.assertRaisesRegex(ValueError, "exatamente 9 números"):
                service.update_game_uid("1234")

    def test_friends_are_saved_per_logged_in_user(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            settings = QSettings(str(root / "settings.ini"), QSettings.Format.IniFormat)
            service = AuthService(root / "accounts.db", settings)
            service.register("Kafka", "kafka@example.com", "stellaron-123")
            service.update_game_uid("600000001")

            friend = service.add_friend(
                "600000002", "Silver Wolf", 70, 6, "https://example.com/icon.png"
            )
            self.assertEqual(service.friends(), [friend])
            self.assertTrue(service.is_friend("600000002"))

            updated = service.add_friend("600000002", "Loba Prateada", 80, 6)
            self.assertEqual(service.friends(), [updated])

            service.register("Himeko", "himeko2@example.com", "expresso-123")
            self.assertEqual(service.friends(), [])
            service.login("Kafka", "stellaron-123")
            self.assertEqual(service.friends(), [updated])
            service.remove_friend("600000002")
            self.assertEqual(service.friends(), [])

    def test_own_uid_cannot_be_added_as_friend(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            settings = QSettings(str(root / "settings.ini"), QSettings.Format.IniFormat)
            service = AuthService(root / "accounts.db", settings)
            service.register("March7th", "march@example.com", "pom-pom-123")
            service.update_game_uid("600000001")
            with self.assertRaisesRegex(ValueError, "principal"):
                service.add_friend("600000001", "March", 70, 6)


if __name__ == "__main__":
    unittest.main()
