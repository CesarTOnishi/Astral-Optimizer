from types import SimpleNamespace
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from app.api.enka_client import (
    AccountFetchWorker,
    GameAssetsUnavailableError,
    _raw_has_unknown_assets,
    _showcase_has_missing_assets,
    _complete_showcase_names,
    classify_account_error,
)
from app.catalog.sync import ensure_relic_set_catalog


class FakeAssets:
    def __init__(self, *, pearl: bool = True, relic: bool = True) -> None:
        self.character_data = {"1503": {}} if pearl else {}
        self.light_cones_data = {"2301": {}}
        self.relic_data = {"41331": {}} if relic else {}


RAW_SHOWCASE = {
    "detailInfo": {"avatarDetailList": [{
        "avatarId": 1503,
        "equipment": {"tid": 2301},
        "relicList": [{"tid": 41331}],
    }]}
}


class FakeClient:
    def __init__(self, *, refresh_works: bool = True) -> None:
        self._assets = FakeAssets(pearl=False, relic=False)
        self.refresh_works = refresh_works
        self.refresh_count = 0
        self.parsed_payloads = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def fetch_showcase(self, uid, *, raw):
        assert raw is True
        return RAW_SHOWCASE

    async def update_assets(self):
        self.refresh_count += 1
        if self.refresh_works:
            self._assets = FakeAssets()

    def parse_showcase(self, payload):
        self.parsed_payloads.append(payload)
        complete = "1503" in self._assets.character_data
        character = SimpleNamespace(
            name="Pearl" if complete else "",
            stats={"HP": 100} if complete else {},
            light_cone=None,
            relics=[SimpleNamespace(
                set_name="Conjunto" if complete else "",
                icon="https://example.test/relic.png" if complete else "",
            )],
        )
        return SimpleNamespace(characters=[character])


class EnkaAssetRefreshTests(unittest.IsolatedAsyncioTestCase):
    def test_unknown_relic_alone_requires_refresh(self) -> None:
        client = SimpleNamespace(_assets=FakeAssets(relic=False))
        self.assertTrue(_raw_has_unknown_assets(client, RAW_SHOWCASE))

    def test_relic_without_name_is_incomplete_even_when_id_is_known(self) -> None:
        character = SimpleNamespace(
            name="Pearl", stats={"HP": 100}, light_cone=None,
            relics=[SimpleNamespace(set_name="", icon="https://example.test/relic.png")],
        )
        self.assertTrue(_showcase_has_missing_assets(
            SimpleNamespace(characters=[character])
        ))

    async def test_missing_translation_uses_catalog_for_character_and_relic(self) -> None:
        relic = SimpleNamespace(set_id=133, set_name="8056168288867632377", icon="url")
        character = SimpleNamespace(
            id=1503, name="17971979440145228372", stats={"HP": 100},
            light_cone=None, relics=[relic],
        )
        showcase = SimpleNamespace(characters=[character])
        catalog = SimpleNamespace(
            characters=lambda: [SimpleNamespace(id="1503", name="Pearl")],
            light_cones=lambda: [],
            relic_set_name=lambda set_id: "Ator Onírico" if set_id == "133" else "",
        )
        with patch("app.api.enka_client.CatalogRepository", return_value=catalog):
            await _complete_showcase_names(showcase)
        self.assertEqual(character.name, "Pearl")
        self.assertEqual(relic.set_name, "Ator Onírico")
        self.assertFalse(_showcase_has_missing_assets(showcase))

    async def test_refreshes_before_parsing_and_reuses_showcase_response(self) -> None:
        client = FakeClient()
        result = object()
        with patch("app.api.enka_client.enka.HSRClient", return_value=client), patch(
            "app.api.enka_client.account_from_showcase", return_value=result
        ):
            account = await AccountFetchWorker("123456789")._fetch()
        self.assertIs(account, result)
        self.assertEqual(client.refresh_count, 1)
        self.assertEqual(client.parsed_payloads, [RAW_SHOWCASE])

    async def test_missing_upstream_data_is_reported_instead_of_blank_cards(self) -> None:
        client = FakeClient(refresh_works=False)
        with patch("app.api.enka_client.enka.HSRClient", return_value=client):
            with self.assertRaises(GameAssetsUnavailableError) as raised:
                await AccountFetchWorker("123456789")._fetch()
        self.assertEqual(client.refresh_count, 1)
        self.assertEqual(
            classify_account_error(raised.exception).code,
            "game_assets_unavailable",
        )

    def test_stale_relic_set_catalog_is_replaced(self) -> None:
        with TemporaryDirectory() as directory:
            target = Path(directory) / "relic_sets.json"
            target.write_text(json.dumps({"132": {"name": "Antigo"}}), encoding="utf-8")
            with patch("app.catalog.sync.catalog_cache_dir", return_value=Path(directory)), patch(
                "app.catalog.sync._download_json",
                return_value={"133": {"name": "Ator Onírico"}},
            ) as download:
                ensure_relic_set_catalog({"133"})
            download.assert_called_once()
            self.assertEqual(
                json.loads(target.read_text(encoding="utf-8"))["133"]["name"],
                "Ator Onírico",
            )


if __name__ == "__main__":
    unittest.main()
