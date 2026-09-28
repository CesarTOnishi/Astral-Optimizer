from types import SimpleNamespace
import unittest

from enka.models.hsr.character import Character

from app.parsers import account_from_showcase


class EnkaParserTests(unittest.TestCase):
    def test_character_without_elemental_bonus_keeps_showcase_available(self) -> None:
        character = Character.model_validate(
            {"level": 1, "avatarId": 1001, "skillTreeList": []}
        )
        showcase = SimpleNamespace(
            characters=[character],
            player=SimpleNamespace(
                nickname="Teste",
                level=1,
                equilibrium_level=0,
                signature="",
                icon="",
                stats=SimpleNamespace(achievement_count=0),
            ),
            uid=123456789,
            ttl=60,
        )

        account = account_from_showcase(showcase)

        self.assertEqual(len(account.characters), 1)
        self.assertEqual(account.characters[0].avatar_id, "1001")
        self.assertEqual(
            account.characters[0].raw["fribbels_payload"]["avatarId"],
            "1001",
        )


if __name__ == "__main__":
    unittest.main()
