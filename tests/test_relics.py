import tempfile
import unittest
from pathlib import Path

from app.models import (
    AccountSummary, CharacterStat, CharacterSummary, RelicSummary,
)
from app.relics import RelicDatabase


def make_relic(critical_damage: float) -> RelicSummary:
    return RelicSummary(
        slot="Mãos",
        slot_key="HAND",
        set_name="Conjunto de teste",
        level=15,
        rarity=5,
        icon_url=f"https://example.test/{critical_damage}.png",
        main_stat=CharacterStat(
            "AttackDelta", "ATQ", 352, "352", False,
        ),
        sub_stats=[
            CharacterStat(
                "CriticalDamage", "Dano Crítico", critical_damage,
                f"{critical_damage:.1f}%", True, upgrades=3,
            )
        ],
    )


def make_character(
    name: str, avatar_id: str, relics: list[RelicSummary]
) -> CharacterSummary:
    return CharacterSummary(
        name=name, avatar_id=avatar_id, level=80, eidolon=0,
        light_cone="Cone", light_cone_level=80, light_cone_rank=1,
        light_cone_icon_url="", relic_count=len(relics), rarity=5,
        element="Vento", path="Caça", icon_url=f"{avatar_id}.png",
        splash_url="", stats=[], relics=relics, raw={},
    )


def make_account(characters: list[CharacterSummary]) -> AccountSummary:
    return AccountSummary(
        uid="600000001", nickname="Teste", level=70, world_level=6,
        signature="", profile_icon_url="", characters=characters, ttl=60,
    )


class RelicDatabaseTests(unittest.TestCase):
    def test_preserves_previous_relics_and_tracks_holder_changes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = RelicDatabase(Path(directory) / "relics.db")
            moved = make_relic(25.9)
            removed = make_relic(5.8)
            database.sync_account(
                7, make_account([make_character("Feixiao", "1220", [moved, removed])])
            )
            database.sync_account(
                7, make_account([make_character("Evanescia", "1505", [moved])])
            )

            relics = database.relics(7, "600000001")
            self.assertEqual(len(relics), 2)
            moved_result = next(
                item for item in relics
                if item.fingerprint == database.fingerprint(moved)
            )
            removed_result = next(
                item for item in relics
                if item.fingerprint == database.fingerprint(removed)
            )
            self.assertEqual(moved_result.current_character_name, "Evanescia")
            self.assertEqual(moved_result.previous_character_name, "Feixiao")
            self.assertFalse(removed_result.is_equipped)
            self.assertEqual(removed_result.previous_character_name, "Feixiao")
            self.assertEqual(
                [item.score for item in relics],
                sorted((item.score for item in relics), reverse=True),
            )

    def test_does_not_mix_local_owners(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = RelicDatabase(Path(directory) / "relics.db")
            account = make_account([make_character("Feixiao", "1220", [make_relic(20)])])
            database.sync_account(1, account)
            self.assertEqual(len(database.relics(1, account.uid)), 1)
            self.assertEqual(database.relics(2, account.uid), [])


if __name__ == "__main__":
    unittest.main()
