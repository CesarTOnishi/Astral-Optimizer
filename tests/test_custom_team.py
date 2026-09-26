import os
import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMainWindow
from app.benchmark.catalog import CatalogEntry
from app.ui.main_window import MainWindow
from app.ui.team_dialog import CustomTeamDialog
from app.ui.widgets import TeamCard
from test_benchmark import character


CATALOG = (
    [CatalogEntry(str(i), f"Character {i}", f"Character{i}", "Hunt", 5) for i in range(1, 5)],
    [CatalogEntry("10", "Cone", "Cone", "Hunt", 5)],
    [CatalogEntry("100", "Relic", "Relic")],
    [CatalogEntry("200", "Ornament", "Ornament")],
)
TEAM = [dict(characterId=str(i), characterEidolon=0, lightCone="10",
             lightConeSuperimposition=1, teamRelicSet=None, teamOrnamentSet=None,
             extra={"preserve": i}) for i in range(1, 4)]


class CustomTeamTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.window = MainWindow.__new__(MainWindow)
        QMainWindow.__init__(self.window)
        self.window.current_account = None
        self.window.current_characters = [character([])]
        self.window.current_character_id = "1220"
        self.window.team_settings = QSettings(str(Path(self.temp.name) / "teams.ini"), QSettings.Format.IniFormat)
        self.window.fribbels_cache = {"global:1220:default": {"teammates": deepcopy(TEAM)}}
        self.window.team_card = TeamCard()
        self.window._display_benchmark = Mock()
        self.window.set_status = Mock()

    def tearDown(self):
        self.window.team_settings.sync()
        self.window.team_card.deleteLater()
        self.window.deleteLater()
        self.temp.cleanup()

    def test_custom_button_seeds_default_and_preserves_existing_custom(self):
        w = self.window
        w.use_custom_team()
        self.assertTrue(w._uses_custom_team("1220"))
        self.assertEqual(w._custom_team("1220"), TEAM)
        edited = deepcopy(TEAM)
        edited[1]["characterEidolon"] = 4
        w.team_settings.setValue(w._team_settings_key("1220", "members"), json.dumps(edited))
        w.use_default_team()
        w.use_custom_team()
        self.assertEqual(w._custom_team("1220"), edited)
        self.assertEqual(w.fribbels_cache["global:1220:default"]["teammates"], TEAM)

    def test_edit_default_switches_to_custom_before_dialog_and_cancel_preserves_copy(self):
        w = self.window
        with patch("app.ui.main_window.CustomTeamDialog") as dialog_type:
            def cancel():
                self.assertTrue(w._uses_custom_team("1220"))
                return 0
            dialog_type.return_value.exec.side_effect = cancel
            w.open_custom_team_dialog(1)
            self.assertEqual(dialog_type.call_args.kwargs["member_index"], 1)
        self.assertEqual(w._custom_team("1220"), TEAM)

    def test_single_editor_changes_only_selected_member_and_validates_duplicates(self):
        with patch("app.ui.team_dialog.load_catalog", return_value=CATALOG):
            dialog = CustomTeamDialog(deepcopy(TEAM), member_index=1)
            try:
                self.assertEqual(len(dialog.editors), 1)
                editor = dialog.editors[0]
                editor.eidolon.setValue(4)
                editor.superimposition.setValue(3)
                editor.relic.setCurrentIndex(1)
                editor.ornament.setCurrentIndex(1)
                output = dialog.team()
                self.assertEqual(output[0], TEAM[0])
                self.assertEqual(output[2], TEAM[2])
                self.assertEqual(output[1]["extra"], TEAM[1]["extra"])
                self.assertEqual(output[1]["teamRelicSet"], "Relic")
                self.assertEqual(output[1]["teamOrnamentSet"], "Ornament")
                self.assertEqual(output[1]["characterEidolon"], 4)
                editor._select_id(editor.character, "1")
                dialog._submit()
                self.assertIn("diferente", dialog.validation.text())
                self.assertEqual(dialog.result(), 0)
                editor._select_id(editor.character, "4")
                dialog._submit()
                self.assertEqual(dialog.result(), 1)
            finally:
                dialog.deleteLater()

    def test_accepted_member_edit_is_saved_and_recalculated(self):
        w = self.window
        w.use_custom_team()
        edited = deepcopy(TEAM)
        edited[2]["teamOrnamentSet"] = "Ornament"
        with patch("app.ui.main_window.CustomTeamDialog") as dialog_type:
            dialog_type.return_value.exec.return_value = 1
            dialog_type.return_value.team.return_value = edited
            w.open_custom_team_dialog(2)
        self.assertEqual(w._custom_team("1220"), edited)
        self.assertTrue(w._uses_custom_team("1220"))
        w._display_benchmark.assert_called_with(w.current_characters[0])

    def test_click_avatar_or_cone_targets_correct_member(self):
        card = self.window.team_card
        received = []
        card.edit_requested.connect(received.append)
        card.show()
        self.app.processEvents()
        for index, visuals in enumerate(card.member_visuals):
            for target in (visuals[1], visuals[3]):
                QTest.mouseClick(target, Qt.MouseButton.LeftButton)
                self.assertEqual(received[-1], index)
        self.assertEqual(received, [0, 0, 1, 1, 2, 2])
        card.hide()
