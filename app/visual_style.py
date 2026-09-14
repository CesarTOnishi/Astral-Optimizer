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
QLabel#muted, QLabel#sectionHint, QLabel#characterMeta { color: #98a8bf; font-size: 11px; }
QLabel#metricTitle, QLabel#statName { color: #9aacc3; font-size: 11px; font-weight: 500; }
QLabel#metricValue, QLabel#warpMetricValue { color: #edf4ff; font-size: 24px; font-weight: 600; }
QLabel#profileUid { color: #a4b8ce; font-size: 11px; }
QLabel#profileSignature { color: #97a9c0; font-style: normal; }
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
