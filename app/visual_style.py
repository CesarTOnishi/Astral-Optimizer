"""Shared visual hierarchy, applied before theme recoloring and accessibility rules."""
from pathlib import Path

REFINED_STYLESHEET = """
QMainWindow, QWidget#appRoot, QWidget#appBody {
    font-family: "Segoe UI", "Bahnschrift"; font-size: 13px;
}
QLabel, QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox,
QTableWidget, QListWidget, QPushButton {
    font-family: "Segoe UI", "Bahnschrift";
}
QLabel#homeTitle, QLabel#sideBrand, QLabel#titleBarTitle {
    font-family: "AR UDJingXiHeiE1B5HK", "Segoe UI";
}
QLabel#sideBrand { font-size: 16px; font-weight: 600; padding: 4px 0; }
QLabel#brandTitle, QLabel#plannerTitle, QLabel#catalogTitle,
QLabel#relicInventoryTitle, QLabel#settingsTitle {
    font-size: 22px; font-weight: 600; letter-spacing: 0px; color: #eef4ff;
}
QLabel#sectionTitle, QLabel#characterSectionTitle {
    font-size: 13px; font-weight: 600; letter-spacing: 0px; color: #d9e3f2;
}
QLabel#detailName, QLabel#catalogDetailName { font-weight: 600; font-size: 24px; }
QLabel#detailName[compactName="true"] { font-size: 19px; }
QFrame#sectionLoadStatus {
    background-color: #132137; border: none; border-radius: 7px;
}
QFrame#sectionLoadStatus[empty="true"] { background-color: transparent; }
QFrame#sectionLoadStatus[state="error"] { background-color: #30202b; }
QLabel#sectionLoadIndicator { color: #72d9f5; font-size: 13px; font-weight: 700; }
QFrame#sectionLoadStatus[state="error"] QLabel#sectionLoadIndicator { color: #ff8fa5; }
QLabel#sectionLoadMessage { color: #9fb2ca; font-size: 10px; }
QPushButton#sectionRetryButton {
    min-height: 18px; padding: 2px 7px; border: none; border-radius: 5px;
    background-color: #24425c; color: #dff7ff; font-size: 9px; font-weight: 600;
}
QPushButton#sectionRetryButton:hover { background-color: #315875; }
QLabel#muted, QLabel#sectionHint, QLabel#characterMeta { color: #98a8bf; font-size: 11px; }
QLabel#metricTitle, QLabel#statName { color: #9aacc3; font-size: 11px; font-weight: 500; }
QLabel#metricValue, QLabel#warpMetricValue { color: #edf4ff; font-size: 24px; font-weight: 600; }
QLabel#relicSummaryChip {
    color: #d4eff8; background-color: #173348; border: 1px solid #315d73;
    border-radius: 8px; padding: 6px 10px; font-size: 10px; font-weight: 700;
}
QFrame#relicFilterPanel {
    border: 1px solid #2b405a; border-radius: 11px; background-color: #111c2e;
}
QWidget#relicFilterItem QComboBox {
    min-height: 27px; padding: 2px 26px 2px 8px; border: 1px solid #385174;
    border-radius: 7px; background-color: #0d1727; font-size: 10px;
}
QWidget#relicFilterItem QLabel#metricTitle {
    color: #8296ae; font-size: 8px; font-weight: 700; padding-left: 2px;
}
QPushButton#relicClearFilters {
    min-height: 22px; padding: 2px 9px; border: 1px solid #31506c;
    border-radius: 7px; background-color: transparent; color: #a7cbe0;
    font-size: 9px; font-weight: 600;
}
QPushButton#relicClearFilters:hover { background-color: #173149; color: #eaf8ff; }
QFrame#inventoryRelicCard {
    background-color: #111d30; border: 1px solid #314766;
    border-left: 3px solid #4d6989; border-radius: 11px;
}
QFrame#inventoryRelicCard[relicState="equipada"] { border-left-color: #5dc9a5; }
QFrame#inventoryRelicCard[relicState="movida"] { border-left-color: #e7bd75; }
QFrame#inventoryRelicCard:hover { background-color: #16283f; border-color: #5c83a3; }
QFrame#relicCard[compactBuild="true"] QLabel#relicSlot { font-size: 10px; }
QFrame#relicCard[compactBuild="true"] QLabel#relicSet { font-size: 11px; }
QFrame#relicCard[compactBuild="true"] QLabel#rowName { font-size: 11px; }
QFrame#relicCard[compactBuild="true"] QLabel#relicMainValue { font-size: 13px; }
QFrame#relicCard[compactBuild="true"] QLabel#relicScoreLabel { font-size: 10px; }
QFrame#relicCard[compactBuild="true"] QLabel#relicScoreValue { font-size: 11px; }
QFrame#artPanel, QFrame#statsPanel, QFrame#relicsPanel {
    background-color: #111c2e; border: 1px solid #263a54; border-radius: 12px;
}
QFrame#benchmarkCard { background-color: #173348; border: 1px solid #2a566d; border-radius: 10px; }
QFrame#relicCard[compactBuild="true"] {
    background-color: #142034; border: 1px solid #29415e; border-radius: 10px;
}
QFrame#relicCard[compactBuild="true"]:hover { border-color: #3f6785; }
QLabel#comboDamage { color: #a9dff0; font-size: 13px; font-weight: 600; }
QFrame#statsPanel QFrame#statRow { padding: 0; border-bottom: 1px solid #21334b; }
QFrame#statsPanel QFrame#benchmarkCard QProgressBar { min-height: 6px; max-height: 6px; }
QFrame#statsPanel QFrame#benchmarkCard, QFrame#statsPanel QFrame#teamCard,
QFrame#statsPanel QFrame#combatStatsCard { background: transparent; border: none; }
QFrame#statsPanel QLabel#detailName { font-size: 20px; }
QFrame#statsPanel QLabel#rowName { font-size: 11px; }
QFrame#statsPanel QLabel#benchmarkScore, QFrame#statsPanel QLabel#benchmarkGrade {
    font-size: 17px; font-weight: 600;
}
QFrame#statsPanel QLabel#comboDamage { font-size: 11px; }
QFrame#statsPanel QLabel#badge, QFrame#statsPanel QLabel#eidolonBadge {
    background: transparent; border: none; padding: 0 3px; font-size: 11px;
}
QFrame#statsPanel QFrame#statRow { border-bottom: 1px dotted #29415e; }
QFrame#statsPanel QLabel#rowValue { font-size: 12px; font-weight: 600; }
QLabel#inventoryRelicSlot { color: #83d8ec; font-size: 9px; font-weight: 700; }
QLabel#inventoryRelicLevel {
    color: #f3d188; background-color: #3a3327; border: 1px solid #675739;
    border-radius: 5px; padding: 1px 5px; font-size: 9px; font-weight: 700;
}
QLabel#inventoryRelicSet { color: #f3f7ff; font-size: 13px; font-weight: 700; }
QLabel#inventoryRelicMeta { color: #f7d576; font-size: 12px; letter-spacing: 1px; }
QLabel#inventoryRelicGrade {
    color: #cceffa; background-color: #1d4052; border: 1px solid #39738c;
    border-radius: 6px; padding: 2px 6px; font-size: 10px; font-weight: 700;
}
QLabel#inventoryRelicScore { color: #ffffff; font-size: 20px; font-weight: 700; }
QFrame#inventoryRelicHolderBand {
    background-color: #16253b; border: 1px solid #2a405c; border-radius: 7px;
}
QLabel#inventoryRelicHolder { color: #d4e0ee; font-size: 10px; font-weight: 600; }
QLabel#inventoryRelicState {
    color: #a9f0ca; background-color: #173b36; border-radius: 5px;
    padding: 3px 6px; font-size: 8px; font-weight: 700;
}
QLabel#inventoryRelicState[relicState="anterior"] { color: #aab9cd; background-color: #263247; }
QLabel#inventoryRelicState[relicState="movida"] { color: #f7cf8d; background-color: #49351f; }
QFrame#inventoryRelicMain {
    background-color: #1c3550; border: 1px solid #315879; border-radius: 8px;
}
QLabel#inventoryMainName { color: #c8d9e9; font-size: 11px; font-weight: 600; }
QLabel#inventoryMainValue { color: #ffffff; font-size: 15px; font-weight: 700; }
QLabel#inventoryRelicSubheading {
    color: #8daac2; font-size: 9px; font-weight: 700; letter-spacing: 1px;
}
QLabel#inventoryRelicSubEmpty { color: #91a8bf; font-size: 10px; padding: 7px; }
QFrame#inventoryRelicSubCell {
    background-color: #14243a; border: 1px solid #283e5a; border-radius: 7px;
}
QLabel#inventorySubName { color: #afc1d5; font-size: 10px; }
QLabel#inventorySubValue { color: #f1f7ff; font-size: 12px; font-weight: 700; }
QLabel#inventoryUpgrade {
    color: #9ce0ee; background-color: #1c4057; border-radius: 4px;
    padding: 0 4px; font-size: 9px; font-weight: 700;
}
QScrollArea#statsScroll, QScrollArea#statsScroll QWidget#qt_scrollarea_viewport,
QScrollArea#statsScroll QWidget#scrollContent {
    background-color: transparent; border: none;
}
QLabel#profileUid { color: #a4b8ce; font-size: 11px; }
QLabel#profileSignature { color: #97a9c0; font-style: normal; }
QFrame#accountProfilePanel QLabel#detailName { font-size: 18px; }
QFrame#accountProfilePanel QLabel#accountProfileAvatar {
    border-radius: 29px; font-size: 20px;
}
QFrame#accountDashboardSection {
    background-color: #111c2e; border: 1px solid #263a54; border-radius: 11px;
}
QFrame#accountMetricCard {
    background-color: #132137; border: 1px solid #29415e; border-radius: 9px;
}
QLabel#accountMetricTitle { color: #95a9c1; font-size: 11px; font-weight: 600; }
QLabel#accountMetricValue { color: #eef7ff; font-size: 28px; font-weight: 700; }
QWidget#accountCompactRow { border-bottom: 1px solid #21334b; }
QWidget#accountCompactRow QLabel#characterName { font-size: 11px; font-weight: 600; }
QWidget#accountCompactRow QLabel#muted { font-size: 11px; }
QLabel#sideSection { color: #8496ae; padding: 6px 8px; font-weight: 500; }
QFrame#sideBar { background-color: #0d1524; border: none; border-radius: 14px; }
QFrame#sidebarUserPanel { background-color: #131f31; border: none; }
QFrame#panel, QFrame#contentPanel, QFrame#accountProfilePanel,
QFrame#warpSummaryCard, QFrame#plannerSettingsCard, QFrame#warpAnalyticsPanel,
QFrame#catalogInfoCard, QFrame#relicFilterPanel, QFrame#buildProfileHeader {
    border: none; border-radius: 12px; background-color: #111c2e;
}
QFrame#statCard { border: none; background-color: #142034; }
QFrame#statCard:hover, QFrame#catalogInfoCard:hover { border: none; background-color: #16243a; }
QFrame#characterHero { border: none; }
QFrame#buildProfileHeader QLabel#profileHeaderName { font-size: 14px; }
QFrame#buildProfileHeader QLabel#profileHeaderBio { font-size: 10px; }
QFrame#buildProfileHeader QLabel#profileHeaderMeta { font-size: 9px; }
QListWidget#portraitList { min-height: 80px; max-height: 80px; }
QLabel#portraitName { font-size: 9px; }
QFrame#customTitleBar { border: none; background: #0d1524; }
QPushButton#navButton, QPushButton#settingsNavButton {
    background-color: transparent; color: #adbed3;
    border: none; border-left: 3px solid transparent;
    border-radius: 8px; padding: 7px 8px; font-size: 12px; font-weight: 500;
    text-align: left;
}
QPushButton#navButton:hover, QPushButton#settingsNavButton:hover {
    background-color: #142238; color: #edf4ff;
}
QPushButton#navButton:checked, QPushButton#settingsNavButton:checked {
    background-color: #19364b; border-left: 3px solid #7ad9f4;
    color: #b8edfa; font-weight: 600;
}
QPushButton#navButton:focus, QPushButton#settingsNavButton:focus {
    border-top: 1px solid #7ad9f4; border-bottom: 1px solid #7ad9f4;
}
QPushButton#primaryButton { font-weight: 600; border-radius: 8px; }
QTableWidget#warpTable, QTableWidget#plannerGoalTable,
QTableWidget#buildComparisonTable, QTableWidget#upgradeComparisonTable {
    background-color: #101b2d; alternate-background-color: #131f32;
    border: none; gridline-color: transparent;
    selection-background-color: #21435b; selection-color: #edf4ff;
}
QTableWidget#warpTable::item, QTableWidget#plannerGoalTable::item,
QTableWidget#buildComparisonTable::item, QTableWidget#upgradeComparisonTable::item {
    border: none; border-bottom: 1px solid #19273b;
}
QTableWidget::item:hover { background-color: #192d43; }
QHeaderView::section {
    background-color: #101b2d; color: #a7bad1; border: none;
    border-bottom: 1px solid #29394f; font-weight: 600;
}
QLabel#relicMainValue { font-size: 14px; font-weight: 600; color: #f1e8f5; }
QLabel#relicSubValue { font-size: 10px; font-weight: 500; }
QLabel#recentWarpName { font-size: 10px; font-weight: 600; }
QFrame#recentWarpCard { border: none; background-color: #142138; border-radius: 10px; }
QScrollBar:vertical { background: transparent; width: 12px; margin: 2px 0; }
QScrollBar:horizontal { background: transparent; height: 12px; margin: 0 2px; }
QScrollBar::handle:vertical { background: #536984; border-radius: 4px; min-height: 28px; }
QScrollBar::handle:horizontal { background: #536984; border-radius: 4px; min-width: 28px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; border: none; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0px; border: none; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }
QScrollBar::up-arrow, QScrollBar::down-arrow,
QScrollBar::left-arrow, QScrollBar::right-arrow { image: none; width: 0; height: 0; }
QAbstractScrollArea::corner { background: transparent; border: none; }
"""

_ICON_DIR = (Path(__file__).resolve().parent / "assets" / "icons").as_posix()
REFINED_STYLESHEET += f"""
QComboBox::down-arrow {{ image: url("{_ICON_DIR}/chevron-down.svg"); width: 14px; height: 14px; }}
QCheckBox::indicator, QCheckBox#experienceCheckBox::indicator {{
    width: 16px; height: 16px; border: 1px solid #72839d;
    border-radius: 4px; background-color: #0c1524;
}}
QCheckBox::indicator:checked, QCheckBox#experienceCheckBox::indicator:checked {{
    image: url("{_ICON_DIR}/check.svg"); background-color: #246080; border-color: #7ad9f4;
}}
"""
