from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from app.catalog import CatalogRepository


class CatalogTests(unittest.TestCase):
    def test_fallback_catalog_is_available_without_download(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = CatalogRepository(Path(directory))
            self.assertGreater(len(repository.characters()), 100)
            self.assertGreater(len(repository.light_cones()), 150)
            self.assertFalse(repository.has_details)

    def test_cached_details_are_linked_and_missing_new_entries_are_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payloads = {
                "characters": {
                    "1001": {
                        "id": "1001", "name": "7 de Março", "rarity": 4,
                        "path": "Knight", "element": "Ice",
                        "skills": ["100101"], "ranks": ["100101"],
                    }
                },
                "character_skills": {
                    "100101": {
                        "id": "100101", "name": "Flecha Glacial",
                        "type_text": "ATQ Básico",
                        "desc": "Causa #1[i]% do ATQ.", "params": [[0.5], [1.4]],
                    }
                },
                "character_ranks": {
                    "100101": {"id": "100101", "name": "Memória", "rank": 1, "desc": "Recupera Energia."}
                },
                "character_promotions": {
                    "1001": {"values": [{"hp": {"base": 489.6, "step": 7.2}}]}
                },
                "light_cones": {
                    "20000": {"id": "20000", "name": "Flechas", "rarity": 3, "path": "Rogue"}
                },
            }
            for name, payload in payloads.items():
                (root / f"{name}.json").write_text(json.dumps(payload), encoding="utf-8")
            repository = CatalogRepository(root)
            march = next(item for item in repository.characters() if item.id == "1001")
            skill = repository.skills_for(march)[0]
            self.assertTrue(repository.has_details)
            self.assertGreater(len(repository.characters()), 100)
            self.assertEqual(repository.format_description(skill.description, skill.parameters[-1]), "Causa 140% do ATQ.")
            self.assertAlmostEqual(repository.character_stats("1001")["hp"], 1058.4)
            self.assertEqual(repository.ranks_for(march)[0].rank, 1)

    def test_only_values_changed_by_superimposition_are_highlighted(self) -> None:
        rendered = CatalogRepository.format_description_rich(
            "Aumenta #1[i]% por #2[i] rodadas.",
            [0.6, 2],
            {0},
        )
        self.assertIn("color:#ffad5c", rendered)
        self.assertIn(">60%</span>", rendered)
        self.assertIn("por 2 rodadas", rendered)
        self.assertNotIn(">2</span>", rendered)


if __name__ == "__main__":
    unittest.main()
