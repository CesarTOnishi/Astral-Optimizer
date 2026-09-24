from pathlib import Path


APP_NAME = "Astral Optimizer"
APP_VERSION = "1.3.0"
GITHUB_REPOSITORY = "CesarTOnishi/Astral-Optimizer"
APP_USER_AGENT = f"AstralOptimizer/{APP_VERSION} (PySide6)"
APP_ASSETS_DIR = Path(__file__).resolve().parent / "assets"
APP_ICON_PNG = APP_ASSETS_DIR / "astral_optimizer.png"
APP_ICON_ICO = APP_ASSETS_DIR / "astral_optimizer.ico"
APP_HOME_BACKGROUND = APP_ASSETS_DIR / "home_background.png"
APP_FONT_TTF = APP_ASSETS_DIR / "fonts" / "RPG_TR.ttf"


APP_STYLESHEET = """
QMainWindow, QWidget#appRoot, QWidget#appBody {
    background-color: #080d19;
    color: #eef4ff;
    font-family: "AR UDJingXiHeiE1B5HK", "Bahnschrift", "Segoe UI";
    font-size: 14px;
}
/* A fonte localizada do jogo não desenha corretamente alguns glifos de
   navegação. Os botões usam uma família DIN compatível para preservar ícones. */
QPushButton, QToolButton {
    font-family: "Segoe UI", "Segoe UI Symbol";
}
QFrame#loadingOverlay { background-color: rgba(5, 9, 18, 218); border: none; }
QFrame#loadingCard {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #17223b, stop:0.55 #1d1d40, stop:1 #301d49);
    border: 1px solid #765a9b; border-radius: 18px;
}
QLabel#loadingTitle { color: #ffffff; font-size: 18px; font-weight: 850; }
QLabel#loadingMessage { color: #b9c6dc; font-size: 11px; }
QProgressBar#loadingProgress {
    min-height: 6px; max-height: 6px; background-color: #11192a;
    border: none; border-radius: 3px; text-align: center;
}
QProgressBar#loadingProgress::chunk {
    border-radius: 3px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #58c8f1, stop:0.5 #d05dde, stop:1 #ff8fc8);
}
QFrame#customTitleBar {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #0c1424, stop:0.55 #111a30, stop:1 #191735);
    border: none; border-bottom: 1px solid #2d3d5e;
}
QWidget#homePage { background-color: #080d19; }
QWidget#homeHeading, QWidget#homeSearchGroup { background-color: transparent; }
QLabel#homeEyebrow {
    color: #a8e7fb; font-size: 10px; font-weight: 850; letter-spacing: 1px;
}
QLabel#homeTitle {
    color: #ffffff; font-size: 29px; font-weight: 850;
    background-color: transparent;
}
QLabel#homeDescription {
    color: #f2f6fc; font-size: 12px; font-weight: 650;
    background-color: transparent;
}
QLabel#homeDescription a { color: #79d8fa; text-decoration: underline; }
QLineEdit#homeUidInput {
    color: #ffffff; background-color: rgba(7, 14, 27, 235);
    border: 1px solid #486782; border-radius: 11px;
    padding: 11px 13px; font-size: 14px; font-weight: 700;
}
QLineEdit#homeUidInput:hover { border-color: #6796b7; }
QLineEdit#homeUidInput:focus { border: 1px solid #82dcfa; }
QPushButton#homeSearchButton {
    color: #ffffff;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #238fc5, stop:1 #7558c8);
    border: 1px solid #88d8f5; border-radius: 11px;
    padding: 11px 18px; font-size: 12px; font-weight: 800;
}
QPushButton#homeSearchButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #32a9dc, stop:1 #8a6bdd);
}
QPushButton#homeSearchButton:disabled {
    color: #73839a; background-color: #26334a; border-color: #394961;
}
QLabel#homeMessage { color: #91a4bd; min-height: 15px; font-size: 10px; }
QLabel#homeMessage[error="true"] { color: #ff9eae; }
QLabel#titleBarMark { color: #78dcff; font-size: 19px; font-weight: 900; }
QLabel#titleBarTitle { color: #f4f7ff; font-size: 13px; font-weight: 800; letter-spacing: 1px; }
QLabel#titleBarSubtitle { color: #697b98; font-size: 10px; }
QPushButton#windowButton, QPushButton#closeWindowButton {
    background-color: transparent; color: #aebbd0; border: none;
    border-radius: 7px; font-size: 15px; font-weight: 650;
}
QPushButton#windowButton:hover { background-color: #263550; color: #ffffff; }
QPushButton#closeWindowButton:hover { background-color: #c94f68; color: #ffffff; }
QPushButton#notificationBell {
    color: #aebbd0; background-color: transparent; border: 1px solid transparent;
    border-radius: 8px; padding: 3px 9px; font-size: 13px; font-weight: 750;
}
QPushButton#notificationBell:hover {
    color: #ffffff; background-color: #263550; border-color: #3d5274;
}
QPushButton#notificationBell[unread="true"] {
    color: #fff0b0; background-color: #322a20; border-color: #7a6334;
}
QPushButton#whatsNewTitleButton {
    color: #a9dff4; background-color: transparent;
    border: 1px solid transparent; border-radius: 8px;
    font-size: 17px; font-weight: 850;
}
QPushButton#whatsNewTitleButton:hover {
    color: #ffffff; background-color: #263550; border-color: #4a668b;
}
QPushButton#whatsNewTitleButton[unseen="true"] {
    color: #fff3b5; background-color: #332841;
    border-color: #9a6fab;
}
QPushButton#activityHistoryButton {
    color: #a9dff4; background-color: transparent;
    border: 1px solid transparent; border-radius: 8px;
}
QPushButton#activityHistoryButton:hover {
    color: #ffffff; background-color: #263550; border-color: #4a668b;
}
QMenu#activityHistoryMenu {
    color: #eef4ff; background-color: #0d1728; border: 1px solid #405b7d;
    border-radius: 11px; padding: 6px;
}
QFrame#activityHistoryHeader { background-color: transparent; border: none; }
QLabel#activityHistoryTitle { color: #f4f8ff; font-size: 12px; font-weight: 850; }
QLabel#activityHistorySummary { color: #8295b1; font-size: 10px; }
QFrame#activityHistoryRow {
    background-color: #121e32; border: 1px solid #263b59; border-radius: 9px;
}
QFrame#activityHistoryRow[kind="error"] { background-color: #281924; border-color: #704052; }
QFrame#activityHistoryRow[kind="warning"] { background-color: #2b2518; border-color: #71603a; }
QLabel#activityHistoryIcon {
    color: #9bdfff; background-color: #193750; border: 1px solid #37708f;
    border-radius: 14px; font-size: 14px; font-weight: 900;
}
QFrame#activityHistoryRow[kind="success"] QLabel#activityHistoryIcon {
    color: #91e6b8; background-color: #17372e; border-color: #34735c;
}
QFrame#activityHistoryRow[kind="error"] QLabel#activityHistoryIcon {
    color: #ffb2be; background-color: #3b202d; border-color: #7b465b;
}
QLabel#activityHistoryEventTitle { color: #f4f8ff; font-size: 11px; font-weight: 800; }
QLabel#activityHistoryMessage { color: #a0afc5; font-size: 10px; }
QLabel#activityHistoryTime { color: #7185a2; font-size: 9px; }
QLabel#activityHistoryEmpty { color: #8295b1; background-color: transparent; }
QPushButton#contextHelpButton {
    color: #8eddf8; background-color: rgba(20,43,66,190);
    border: 1px solid #345f7c; border-radius: 13px; padding: 0px;
}
QPushButton#contextHelpButton:hover {
    color: #ffffff; background-color: #205477; border-color: #79d8f5;
}
QPushButton#contextHelpButton:pressed { background-color: #10263c; }
QFrame#contextHelpPopup {
    color: #eef4ff; background-color: #0e1829;
    border: 1px solid #3d5b7a; border-radius: 14px;
}
QWidget#contextHelpContent { background-color: transparent; }
QFrame#contextHelpHeader { background-color: transparent; border: none; }
QFrame#contextHelpIconPlate {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #174862, stop:1 #26365d);
    border: 1px solid #4383a3; border-radius: 10px;
}
QLabel#contextHelpEyebrow {
    color: #70d8fa; font-size: 8px; font-weight: 850; letter-spacing: 1px;
}
QLabel#contextHelpTitle {
    color: #f7f9ff; font-size: 13px; font-weight: 800;
}
QPushButton#contextHelpClose {
    color: #8fa1ba; background-color: transparent; border: 1px solid transparent;
    border-radius: 7px; padding: 0px;
}
QPushButton#contextHelpClose:hover {
    color: #ffffff; background-color: #243650; border-color: #3e5878;
}
QFrame#contextHelpBody {
    background-color: #121f33; border: 1px solid #233a56; border-radius: 10px;
}
QLabel#contextHelpText {
    color: #bdc9da; font-size: 10px; line-height: 1.35;
}
QMenu#notificationMenu {
    color: #eef4ff; background-color: #10192b; border: 1px solid #40567a;
    border-radius: 10px; padding: 5px;
}
QFrame#notificationRow { background-color: #131f34; border-radius: 8px; }
QFrame#notificationRow:hover { background-color: #192a45; }
QLabel#notificationIcon {
    color: #9bddff; background-color: #193550; border: 1px solid #326080;
    border-radius: 12px; font-weight: 850;
}
QFrame#notificationRow[kind="success"] QLabel#notificationIcon {
    color: #91e6b8; background-color: #17372e; border-color: #34735c;
}
QFrame#notificationRow[kind="warning"] QLabel#notificationIcon,
QFrame#notificationRow[kind="error"] QLabel#notificationIcon {
    color: #ffd39a; background-color: #3a2a24; border-color: #7e5841;
}
QLabel#notificationTitle { color: #f5f8ff; font-size: 11px; font-weight: 800; }
QLabel#notificationMessage { color: #9cabc2; font-size: 10px; }
QLabel#notificationEmpty { color: #8d9db5; background-color: #10192b; }
QSizeGrip#windowSizeGrip { background-color: transparent; }
QLabel { background: transparent; }
QLabel#brandMark { color: #78dcff; font-size: 28px; font-weight: 800; }
QLabel#brandTitle { color: #f6f8ff; font-size: 20px; font-weight: 750; letter-spacing: 1px; }
QLabel#muted, QLabel#footer, QLabel#characterMeta, QLabel#sectionHint { color: #8290aa; }
QLabel#footer { font-size: 11px; }
QPushButton#syncStatus {
    color: #8290aa; background-color: #0d1728; border: 1px solid #263a57;
    border-radius: 8px; padding: 7px 8px; font-size: 9px; font-weight: 750;
}
QPushButton#syncStatus:hover { color: #d8e8fa; border-color: #496887; }
QPushButton#syncStatus[status="syncing"] {
    color: #91e5ff; background-color: #10283a; border-color: #356985;
}
QPushButton#syncStatus[status="success"] {
    color: #8ce5b7; background-color: #102c28; border-color: #316a57;
}
QPushButton#syncStatus[status="error"] {
    color: #ff9cab; background-color: #321a26; border-color: #704052;
}
QMenu#taskCenterMenu {
    color: #eef4ff; background-color: #0d1728; border: 1px solid #405b7d;
    border-radius: 11px; padding: 6px;
}
QFrame#taskCenterHeader { background-color: transparent; border: none; }
QLabel#taskCenterTitle { color: #f4f8ff; font-size: 12px; font-weight: 850; }
QLabel#taskCenterSummary { color: #8295b1; font-size: 10px; }
QPushButton#taskCenterClear {
    color: #91cfe8; background-color: transparent; border: none;
    padding: 5px 7px; font-size: 10px; font-weight: 700;
}
QPushButton#taskCenterClear:hover { color: #ffffff; background-color: #1b2b45; border-radius: 6px; }
QFrame#taskCenterRow {
    background-color: #121e32; border: 1px solid #263b59; border-radius: 9px;
}
QFrame#taskCenterRow[state="active"] { border-color: #356681; background-color: #11263a; }
QFrame#taskCenterRow[state="error"] { border-color: #704052; background-color: #281924; }
QLabel#taskCenterIcon {
    color: #9bdfff; background-color: #193750; border: 1px solid #37708f;
    border-radius: 14px; font-size: 14px; font-weight: 900;
}
QFrame#taskCenterRow[state="success"] QLabel#taskCenterIcon {
    color: #91e6b8; background-color: #17372e; border-color: #34735c;
}
QFrame#taskCenterRow[state="error"] QLabel#taskCenterIcon {
    color: #ffb2be; background-color: #3b202d; border-color: #7b465b;
}
QLabel#taskCenterTaskTitle { color: #f4f8ff; font-size: 11px; font-weight: 800; }
QLabel#taskCenterMessage { color: #a0afc5; font-size: 10px; }
QLabel#taskCenterState {
    color: #90dff7; background-color: #18354c; border-radius: 6px;
    padding: 2px 6px; font-size: 8px; font-weight: 850;
}
QLabel#taskCenterState[state="success"] { color: #91e6b8; background-color: #17372e; }
QLabel#taskCenterState[state="error"] { color: #ffb2be; background-color: #3b202d; }
QPushButton#taskCenterAction {
    color: #ccecff; background-color: #193653; border: 1px solid #3d6e91;
    border-radius: 6px; padding: 5px 9px; font-size: 9px; font-weight: 750;
}
QPushButton#taskCenterAction:hover { color: #ffffff; background-color: #245077; border-color: #68b8df; }
QLabel#taskCenterEmpty { color: #8295b1; background-color: transparent; }
QFrame#searchPanel, QFrame#heroPanel, QFrame#contentPanel,
QFrame#characterHero, QFrame#statCard {
    border: 1px solid #263452;
    border-radius: 14px;
}
QFrame#searchPanel { background-color: #10182a; }
QFrame#heroPanel {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #15213b, stop:0.55 #121c34, stop:1 #1b1838);
    border: 1px solid #35486f;
}
QFrame#contentPanel { background-color: #0e1627; }
QFrame#characterHero {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #172544, stop:0.52 #17213a, stop:1 #261b43);
    border: 1px solid #3a4d78;
}
QFrame#statCard { background-color: #111b2f; border: 1px solid #253657; }
QFrame#statCard:hover { background-color: #16233c; border: 1px solid #41638e; }
QLabel#profileName { color: #ffffff; font-size: 24px; font-weight: 750; }
QLabel#profileUid { color: #7fdcff; font-size: 12px; font-weight: 650; }
QLabel#profileSignature { color: #9ca9bf; font-style: italic; }
QLabel#metricTitle, QLabel#statName { color: #8e9bb4; font-size: 11px; font-weight: 700; }
QLabel#metricValue { color: #ffffff; font-size: 19px; font-weight: 750; }
QLabel#sectionTitle { color: #eaf1ff; font-size: 15px; font-weight: 750; }
QLabel#characterName { color: #ffffff; font-size: 15px; font-weight: 700; }
QLabel#detailName { color: #ffffff; font-size: 24px; font-weight: 800; }
QLabel#rarity { color: #f2ca72; font-size: 14px; }
QLabel#badge {
    color: #bdeeff; background-color: #17334b; border: 1px solid #295b78;
    border-radius: 9px; padding: 4px 9px; font-size: 11px; font-weight: 700;
}
QLabel#eidolonBadge {
    color: #f4d68e; background-color: #382d24; border: 1px solid #6b5836;
    border-radius: 9px; padding: 4px 9px; font-size: 11px; font-weight: 750;
}
QLabel#statValue { color: #f8fbff; font-size: 19px; font-weight: 750; }
QLabel#statIcon {
    color: #78dcff; background-color: #162b44; border: 1px solid #274c70;
    border-radius: 10px; font-size: 16px; font-weight: 800;
}
QLineEdit {
    background-color: #0a1221; color: #f4f7ff; border: 1px solid #304465;
    border-radius: 10px; padding: 11px 13px; selection-background-color: #417fba;
}
QLineEdit:focus { border: 1px solid #69cffa; }
QComboBox {
    color: #eaf2ff; background-color: #0d1729;
    border: 1px solid #334967; border-radius: 9px;
    padding: 7px 34px 7px 11px; min-height: 20px;
    selection-background-color: #31567d;
}
QComboBox:hover {
    background-color: #111f35; border-color: #52779d;
}
QComboBox:focus, QComboBox:on {
    background-color: #12233c; border: 1px solid #69bde7;
}
QComboBox:disabled {
    color: #66758d; background-color: #101725; border-color: #27354b;
}
QComboBox::drop-down {
    subcontrol-origin: padding; subcontrol-position: top right;
    width: 29px; border: none; border-left: 1px solid #2d4260;
    border-top-right-radius: 8px; border-bottom-right-radius: 8px;
    background-color: rgba(74, 111, 151, 35);
}
QComboBox::drop-down:hover { background-color: rgba(87, 145, 187, 80); }
QComboBox::down-arrow { width: 11px; height: 11px; }
QComboBox QAbstractItemView {
    color: #eaf2ff; background-color: #111c30;
    border: 1px solid #49688f; border-radius: 8px;
    padding: 5px; outline: 0px;
    selection-color: #ffffff; selection-background-color: #294d73;
}
QComboBox QAbstractItemView::item {
    min-height: 30px; padding: 3px 8px; border-radius: 6px;
}
QSpinBox {
    color: #f5f8ff; background-color: #0d1729;
    border: 1px solid #334967; border-radius: 9px;
    padding: 7px 11px; min-height: 20px;
    font-size: 13px; font-weight: 750;
    selection-color: #ffffff; selection-background-color: #31567d;
}
QSpinBox:hover {
    background-color: #111f35; border-color: #52779d;
}
QSpinBox:focus {
    background-color: #12233c; border-color: #69cffa;
}
QSpinBox:disabled {
    color: #66758d; background-color: #101725; border-color: #27354b;
}
QSpinBox::up-button, QSpinBox::down-button {
    width: 0px; height: 0px; border: none; background: transparent;
}
QPushButton#primaryButton {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3c8fd1, stop:1 #725ec9);
    color: white; border: 1px solid #78c9f0; border-radius: 10px;
    padding: 11px 20px; font-weight: 750;
}
QPushButton#primaryButton:hover { background-color: #559fd8; }
QPushButton#primaryButton:pressed { padding-top: 12px; }
QPushButton#primaryButton:disabled {
    background-color: #28334a; color: #79859b; border-color: #354159;
}
QPushButton#secondaryButton {
    background-color: #151f35; color: #cbd7ea; border: 1px solid #344765;
    border-radius: 9px; padding: 10px 14px; font-weight: 700;
}
QPushButton#secondaryButton:hover { background-color: #1d2c48; border-color: #547399; }
QPushButton#secondaryButton:disabled { color: #6f7b90; border-color: #28364d; }
QPushButton#headerRefreshButton {
    color: #c9efff; background-color: #132b43; border: 1px solid #376486;
    border-radius: 9px; padding: 8px 13px; font-size: 11px; font-weight: 750;
}
QPushButton#headerRefreshButton:hover {
    color: #ffffff; background-color: #1b3b59; border-color: #61b8e2;
}
QPushButton#headerRefreshButton:pressed { background-color: #10243a; }
QPushButton#headerRefreshButton:disabled {
    color: #71829b; background-color: #121c2d; border-color: #293a52;
}
QListWidget { background: transparent; border: none; outline: none; padding: 2px; }
QListWidget::item {
    background-color: #111b2e; border: 1px solid #202f4b;
    border-radius: 12px; margin: 4px 0;
}
QListWidget::item:hover { background-color: #17253d; border-color: #365778; }
QListWidget::item:selected { background-color: #1b2e4d; border: 1px solid #58bce8; }
QLabel#statusInfo, QLabel#statusSuccess, QLabel#statusError {
    border-radius: 9px; padding: 7px 11px; font-size: 12px;
}
QLabel#statusInfo { color: #a8c8e8; background-color: #11243a; }
QLabel#statusSuccess { color: #83e2b1; background-color: #102d29; }
QLabel#statusError { color: #ff9b9b; background-color: #321b27; }
QFrame#settingsUpdatePanel {
    background-color: #101a2d; border: 1px solid #2d4263; border-radius: 10px;
}
QFrame#settingsPrivacyPanel {
    background-color: #101a2d; border: 1px solid #2d4263; border-radius: 10px;
}
QCheckBox#privacyCheckBox {
    color: #eaf2ff; spacing: 9px; font-size: 11px; font-weight: 700;
}
QLabel#privacyHint { color: #8392aa; font-size: 10px; }
QLabel#settingsVersion {
    color: #8edfff; font-size: 10px; font-weight: 750;
}
QLabel#updateVersion {
    color: #8ee1ff; background-color: #14283f; border: 1px solid #315572;
    border-radius: 8px; padding: 8px 10px; font-size: 11px; font-weight: 800;
}
QScrollArea, QWidget#scrollContent { background-color: #0e1627; border: none; }
QScrollArea QWidget#qt_scrollarea_viewport { background-color: #0e1627; }
QScrollArea#buildScroll, QWidget#buildScrollContent { background-color: #080d19; border: none; }
QScrollArea#buildScroll QWidget#qt_scrollarea_viewport { background-color: #080d19; }
QScrollBar:vertical { background: #0b1322; width: 8px; margin: 3px; }
QScrollBar::handle:vertical { background: #314666; border-radius: 4px; min-height: 36px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QSplitter::handle { background: #080d19; width: 12px; }
QFrame#selectorPanel, QFrame#artPanel, QFrame#statsPanel, QFrame#relicsPanel {
    background-color: #171a35;
    border: 1px solid #42466c;
    border-radius: 9px;
}
QFrame#buildProfileHeader {
    background-color: #111b2e;
    border: 1px solid #344868;
    border-radius: 10px;
}
QLabel#profileHeaderName { color: #ffffff; font-size: 16px; font-weight: 850; }
QLabel#profileHeaderBio { color: #b9c5da; font-size: 11px; }
QLabel#profileHeaderMeta { color: #79bfff; font-size: 10px; font-weight: 700; }
QPushButton#copyUidButton {
    color: #dceaff; background-color: #172842; border: 1px solid #3c5b82;
    border-radius: 7px; padding: 7px 10px; font-size: 10px; font-weight: 750;
}
QPushButton#copyUidButton:hover { background-color: #213b60; border-color: #68a8e5; }
QPushButton#copyUidButton:disabled { color: #66758d; background-color: #111a2a; }
QFrame#artPanel {
    background: qlineargradient(x1:0, y1:0, x2:0.8, y2:1,
        stop:0 #6b536d, stop:0.48 #4b416a, stop:1 #292b55);
}
QFrame#lightConeBannerHolder { background: transparent; border: none; }
QFrame#lightConeBanner { background-color: #101a2d; border: none; }
QLabel#lightConeBannerCaption {
    color: #ffffff; background-color: rgba(7,11,21,205);
    border: 1px solid rgba(218,228,246,75); border-radius: 6px;
    padding: 4px 10px; font-size: 10px; font-weight: 800;
}
QFrame#statsPanel {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #3e3767, stop:1 #292c59);
}
QFrame#buildHistoryBar {
    background-color: rgba(12,20,37,205); border: 1px solid #40577a;
    border-radius: 9px;
}
QFrame#buildHistoryPanel {
    background-color: #171d35; border: 1px solid #424c73; border-radius: 11px;
}
QLabel#buildHistoryTitle {
    color: #b9ddff; font-size: 9px; font-weight: 850;
}
QLabel#buildHistoryCounter {
    color: #9deaff; background-color: #15364e; border: 1px solid #34708e;
    border-radius: 7px; padding: 1px 7px; font-size: 8px; font-weight: 850;
}
QComboBox#buildHistorySelector {
    min-height: 18px; padding: 5px 28px 5px 9px; border-radius: 7px;
    font-size: 9px;
}
QPushButton#buildHistorySave, QPushButton#buildHistoryExport, QPushButton#buildHistoryCompare,
QPushButton#buildHistoryDelete {
    color: #dceaff; background-color: #172943; border: 1px solid #3a5679;
    border-radius: 7px; padding: 6px 7px; font-size: 8px; font-weight: 800;
}
QPushButton#buildHistorySave:hover, QPushButton#buildHistoryExport:hover,
QPushButton#buildHistoryCompare:hover {
    color: #ffffff; background-color: #214268; border-color: #65b8e2;
}
QPushButton#buildHistoryDelete { color: #ffb0ba; }
QPushButton#buildHistoryDelete:hover {
    color: #ffffff; background-color: #58263a; border-color: #b65370;
}
QPushButton#buildHistorySave:disabled, QPushButton#buildHistoryExport:disabled,
QPushButton#buildHistoryCompare:disabled,
QPushButton#buildHistoryDelete:disabled {
    color: #65738a; background-color: #111a2a; border-color: #29384f;
}
QFrame#relicsPanel { background-color: #242552; }
QWidget#warpPage { background-color: #080d19; }
QScrollArea#warpPageScroll {
    background-color: #080d19; border: none;
}
QWidget#warpPageContent { background-color: #080d19; }
QWidget#accountPage { background-color: #080d19; }
QWidget#friendsPage, QWidget#friendsContent { background-color: #080d19; }
QScrollArea#friendsScroll { background-color: transparent; border: none; }
QFrame#accountProfilePanel {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #111d32, stop:0.55 #17213b, stop:1 #281d43);
    border: 1px solid #3a5277; border-radius: 14px;
}
QFrame#buildEmptyPanel {
    background-color: #0e1627; border: 1px dashed #304563; border-radius: 13px;
}
QLabel#buildEmptyIcon { color: #68cdea; font-size: 44px; font-weight: 800; }
QLabel#accountProfileAvatar {
    color: #ffffff; background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #2b9cca, stop:1 #7955c8);
    border: 2px solid #8adcf4; border-radius: 39px;
    font-size: 28px; font-weight: 900;
}
QLabel#friendsCount {
    color: #9ee5ff; background-color: #152c44; border: 1px solid #315979;
    border-radius: 10px; padding: 6px 11px; font-size: 10px; font-weight: 800;
}
QFrame#friendCard {
    background-color: #111b2f; border: 1px solid #2b4161; border-radius: 12px;
}
QFrame#friendCard:hover { background-color: #16243b; border-color: #47729a; }
QLabel#friendName { color: #ffffff; font-size: 16px; font-weight: 800; }
QFrame#friendsEmptyCard {
    background-color: #0e1627; border: 1px dashed #304563; border-radius: 13px;
}
QLabel#friendsEmptyIcon { color: #73d7f2; font-size: 38px; font-weight: 800; }
QPushButton#friendViewButton, QPushButton#addFriendButton {
    color: #dff7ff; background-color: #173650; border: 1px solid #3c7497;
    border-radius: 9px; padding: 9px 14px; font-weight: 750;
}
QPushButton#friendViewButton:hover, QPushButton#addFriendButton:hover {
    color: #ffffff; background-color: #215071; border-color: #70cbe9;
}
QPushButton#addFriendButton:disabled {
    color: #8fe3b0; background-color: #17362f; border-color: #39765e;
}
QPushButton#friendRemoveButton {
    color: #9aaac0; background-color: #172137; border: 1px solid #33445f;
    border-radius: 9px; font-size: 18px; font-weight: 700;
}
QPushButton#friendRemoveButton:hover {
    color: #ffffff; background-color: #54263a; border-color: #9a4963;
}
QFrame#warpControlPanel, QFrame#warpSummaryCard {
    background-color: #111b2f; border: 1px solid #2b3d5e; border-radius: 10px;
}
QLabel#warpImportRequirement {
    color: #ffd29b; background-color: #30251c; border: 1px solid #624a32;
    border-radius: 8px; padding: 7px 10px; font-size: 10px; font-weight: 750;
}
QFrame#warpBannerPanel, QFrame#warpDetailsPanel {
    background-color: #0e1627; border: 1px solid #293a59; border-radius: 10px;
}
QFrame#warpAnalyticsPanel {
    background-color: #0e1627; border: 1px solid #293a59; border-radius: 10px;
}
QLabel#warpAnalyticsMetric {
    color: #dbeaff; background-color: #14233a; border: 1px solid #304867;
    border-radius: 8px; padding: 9px 11px; font-size: 11px; font-weight: 700;
}
QLabel#warpGapReport {
    color: #8fe0b5; background-color: #112a27; border: 1px solid #315d50;
    border-radius: 8px; padding: 9px 11px; font-size: 10px;
}
QLabel#warpGapReport[warning="true"] {
    color: #ffd29b; background-color: #32251f; border-color: #6b4d38;
}
QScrollArea#warpBannerScroll {
    background-color: transparent; border: none;
}
QWidget#warpBannerContent { background-color: transparent; }
QPushButton#warpBannerButton {
    background-color: #171b28; color: #dce5f3; border: 1px solid #30394b;
    border-radius: 9px; padding: 5px 10px; text-align: left;
    font-size: 11px; font-weight: 700;
}
QPushButton#warpBannerButton:hover { background-color: #202a3d; border-color: #506684; }
QPushButton#warpBannerButton:checked {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #203c5d, stop:1 #332d5c);
    color: #ffffff; border: 1px solid #82cbed;
}
QFrame#warpSummaryCard:hover { border-color: #496889; background-color: #14223a; }
QLabel#warpMetricValue { color: #8edfff; font-size: 23px; font-weight: 800; }
QListWidget#recentWarpsList {
    background-color: #111722; border: none; border-radius: 9px;
    padding: 5px;
}
QListWidget#recentWarpsList::item { background: transparent; border: none; margin: 0; }
QListWidget#recentWarpsList::item:hover,
QListWidget#recentWarpsList::item:selected { background: transparent; border: none; }
QFrame#recentWarpCard {
    background-color: #1a2130; border: 1px solid #343e52; border-radius: 8px;
}
QLabel#recentPityBadge {
    color: #ffffff; border-radius: 8px;
    padding: 2px 6px; font-size: 10px; font-weight: 850;
}
QLabel#recentPityBadge[pityLevel="low"] { background-color: #24835f; }
QLabel#recentPityBadge[pityLevel="medium"] { background-color: #c9792c; }
QLabel#recentPityBadge[pityLevel="high"] { background-color: #c54350; }
QLabel#recentOutcomeBadge {
    color: #ffffff; background-color: #29364b; border: 1px solid #52637d;
    border-radius: 10px; font-size: 12px; font-weight: 900;
}
QLabel#recentOutcomeBadge[outcome="won"] {
    color: #8ff0be; background-color: #1b513e; border-color: #3ca978;
}
QLabel#recentOutcomeBadge[outcome="guaranteed"] {
    color: #ffd77f; background-color: #5b421b; border-color: #c68c32;
}
QLabel#recentOutcomeBadge[outcome="lost"] {
    color: #ff98a2; background-color: #5a252d; border-color: #c7505d;
}
QLabel#recentWarpName { color: #cbd5e5; font-size: 8px; font-weight: 650; }
QTableWidget#warpTable {
    background-color: #0e1627; alternate-background-color: #111d32;
    color: #edf3ff; border: 1px solid #293a59; border-radius: 9px;
    selection-background-color: #263f65; selection-color: #ffffff;
}
QTableWidget#warpTable::item { padding: 7px; border-bottom: 1px solid #1d2a42; }
QComboBox#accountSelector {
    background-color: #0b1425; color: #dce8f8; border: 1px solid #344b6d;
    border-radius: 8px; padding: 8px 10px; font-weight: 700;
}
QComboBox#accountSelector:hover { border-color: #5791b8; }
QComboBox#accountSelector:disabled { color: #66748a; border-color: #26344b; }
QComboBox#accountSelector QAbstractItemView {
    background-color: #111c30; color: #e8effb; border: 1px solid #3c5274;
    selection-background-color: #29496d; outline: none;
}
QHeaderView::section {
    background-color: #151f35; color: #9eabc1; border: none;
    border-bottom: 1px solid #354764; padding: 8px; font-size: 11px; font-weight: 750;
}
QFrame#relicCard {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #404574, stop:1 #783e76);
    border: 1px solid #6e6792;
    border-radius: 8px;
}
QFrame#relicCard:hover { border: 1px solid #e5b7ee; }
QFrame#statRow { border-bottom: 1px solid rgba(255,255,255,30); }
QFrame#benchmarkCard {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #24264f, stop:1 #4b2d61);
    border: 1px solid #766589; border-radius: 9px;
}
QFrame#benchmarkAnalysisPanel {
    background-color: #171d35;
    border: 1px solid #424c73;
    border-radius: 11px;
}
QLabel#benchmarkPageTitle {
    color: #91bfff; font-size: 18px; font-weight: 850;
}
QLabel#benchmarkSectionTitle {
    color: #c7d3ee; font-size: 17px; font-weight: 800;
}
QFrame#upgradeComparisonCard { background-color: transparent; border: none; }
QFrame#abilityBreakdownCard {
    background-color: #17233d; border: 1px solid #40577f; border-radius: 10px;
}
QLabel#abilityBreakdownTitle { color: #f0b15e; font-size: 12px; font-weight: 850; }
QLabel#abilityBreakdownSubtitle { color: #8799b8; font-size: 9px; }
QLabel#abilityBreakdownExact {
    color: #9ee7c2; background-color: #17382f; border: 1px solid #34725d;
    border-radius: 7px; padding: 4px 8px; font-size: 8px; font-weight: 850;
}
QFrame#abilityDamageRow {
    background-color: #1d2c4a; border: none; border-radius: 6px;
}
QFrame#abilityDamageRow[alternate="true"] { background-color: #223454; }
QLabel#abilityDamageNumber {
    color: #8496b4; background-color: #111b2e; border-radius: 8px;
    min-width: 17px; min-height: 17px; max-width: 17px; max-height: 17px;
    font-size: 8px; font-weight: 800;
}
QLabel#abilityDamageIcon { color: #74d3ef; min-width: 16px; font-size: 11px; font-weight: 850; }
QLabel#abilityDamageName { color: #dce5f6; font-size: 10px; font-weight: 650; }
QLabel#abilityDamageValue { color: #b9d8ff; font-size: 10px; font-weight: 800; min-width: 72px; }
QLabel#abilityBreakdownTotal {
    color: #f2c47e; border-top: 1px solid #344b70;
    padding-top: 7px; font-size: 10px; font-weight: 850;
}
QTableWidget#upgradeComparisonTable {
    background-color: #24375d;
    alternate-background-color: #293f69;
    color: #e5eafa;
    border: 1px solid #48618d;
    border-radius: 7px;
    gridline-color: #48618d;
    font-size: 11px;
}
QTableWidget#upgradeComparisonTable::item {
    padding: 6px;
    border-bottom: 1px solid #48618d;
}
QWidget#comparisonCell { background-color: transparent; }
QLabel#comparisonLabel { color: #e5eafa; font-size: 11px; }
QLabel#comparisonArrow { color: #b8c4dc; font-size: 13px; font-weight: 800; }
QTableWidget#upgradeComparisonTable QHeaderView::section {
    background-color: #1c2b49;
    color: #dce5fa;
    border: none;
    border-right: 1px solid #3e557f;
    border-bottom: 1px solid #5874a6;
    padding: 7px 4px;
    font-size: 10px;
    font-weight: 800;
}
QFrame#teamCard {
    background-color: rgba(18,20,39,150); border: 1px solid #62567d;
    border-radius: 9px;
}
QPushButton#teamModeButton {
    color: #98a8c2; background-color: #111a2d; border: 1px solid #34445f;
    border-radius: 5px; padding: 3px 5px; font-size: 9px; font-weight: 700;
}
QPushButton#teamModeButton:hover { color: #ffffff; background-color: #1d3150; }
QPushButton#teamModeButton:checked {
    color: #dff8ff; background-color: #23537a; border-color: #5bbce9;
}
QDialog#customTeamDialog {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #08111f, stop:0.55 #0b1425, stop:1 #11152b);
    color: #e8edf8;
}
QDialog#customTeamDialog QScrollArea {
    background-color: transparent; border: none;
}
QDialog#customTeamDialog QWidget#scrollContent { background-color: transparent; }
QDialog#customTeamDialog QComboBox QLineEdit {
    color: #edf6ff; background-color: transparent; border: none;
    border-radius: 0; padding: 0 3px; selection-background-color: #31567d;
}
QFrame#customTeamHeader {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #172b47, stop:0.55 #17223d, stop:1 #251d42);
    border: 1px solid #3d587c; border-radius: 13px;
}
QLabel#customTeamMark {
    color: #b5f1ff; background-color: #173d5d; border: 1px solid #5eb5dc;
    border-radius: 19px; min-width: 38px; min-height: 38px;
    max-width: 38px; max-height: 38px; font-size: 19px; font-weight: 900;
}
QLabel#customTeamTitle { color: #ffffff; font-size: 17px; font-weight: 850; }
QLabel#customTeamSubtitle { color: #aebed5; font-size: 10px; }
QLabel#teamSelectionStatus {
    color: #f2ca89; background-color: #322b27; border: 1px solid #665138;
    border-radius: 9px; padding: 6px 10px; font-size: 10px; font-weight: 800;
}
QLabel#teamSelectionStatus[state="ready"] {
    color: #9ff2c9; background-color: #17362f; border-color: #36735d;
}
QLabel#teamSearchTip {
    color: #a9dffc; background-color: rgba(30,72,103,105);
    border: 1px solid #2d5878; border-radius: 8px; padding: 7px 11px;
    font-size: 10px;
}
QFrame#teamEditorCard {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #111d31, stop:1 #161a32);
    border: 1px solid #334c70; border-radius: 12px;
}
QFrame#teamEditorCard:hover { border-color: #547ba5; }
QLabel#teamPositionBadge {
    color: #8edff8; background-color: #142d47; border: 1px solid #315c7b;
    border-radius: 8px; min-width: 29px; min-height: 29px;
    max-width: 29px; max-height: 29px; font-size: 10px; font-weight: 850;
}
QLabel#teamEditorName { color: #ffffff; font-size: 14px; font-weight: 850; }
QLabel#teamEditorPath { color: #7dbfe3; font-size: 9px; font-weight: 700; }
QLabel#teamGroupLabel {
    color: #8297b6; border-bottom: 1px solid #263b59;
    padding: 4px 0 2px 0; font-size: 8px; font-weight: 850;
}
QFrame#teamDialogFooter {
    background-color: rgba(15,25,43,210); border: 1px solid #304663;
    border-radius: 11px;
}
QLabel#teamValidation { color: #ff9fa9; font-size: 10px; font-weight: 700; }
QFrame#combatStatsCard {
    background-color: rgba(18,20,39,150); border: 1px solid #62567d;
    border-radius: 9px;
}
QLabel#characterIdentityIcon {
    background-color: rgba(34,49,78,175); border: 1px solid #40597d;
    border-radius: 15px;
}
QLabel#combatStatName { color: #d9dceb; font-size: 11px; }
QLabel#combatStatValue { color: #f2f3fb; font-size: 11px; font-weight: 650; }
QLabel#combatStatBuffed { color: #8ee6ac; font-size: 11px; font-weight: 800; }
QLabel#teamMemberName { color: #f2f3fb; font-size: 12px; font-weight: 700; }
QLabel#teamMemberDetail { color: #aeb4c9; font-size: 10px; }
QLabel#teamBuildBadge {
    color: #e9efff; background-color: #090d18; border: 1px solid #56637e;
    border-radius: 4px; padding: 0 4px; font-size: 8px; font-weight: 800;
    min-width: 20px; max-height: 12px;
}
QWidget#teamMemberClickable {
    background-color: transparent; border: 1px solid transparent;
    border-radius: 7px;
}
QWidget#teamMemberClickable:hover {
    background-color: rgba(73,120,164,55); border-color: #426789;
}
QLabel#benchmarkTitle { color: #d9dff5; font-size: 11px; font-weight: 800; }
QLabel#betaBadge {
    color: #ffd68a; background-color: #493a25; border: 1px solid #80643b;
    border-radius: 5px; padding: 2px 6px; font-size: 8px; font-weight: 800;
    max-height: 18px;
}
QLabel#benchmarkScore { color: #ffcb7c; font-size: 23px; font-weight: 850; }
QLabel#benchmarkGrade { color: #ffd0f4; font-size: 18px; font-weight: 850; }
QProgressBar { background-color: #15182d; border: none; border-radius: 4px; height: 8px; }
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #eb665e, stop:0.48 #d9e94f, stop:0.72 #50cf72, stop:1 #4bbce9);
    border-radius: 4px;
}
QFrame#upgradeRow { background-color: rgba(18,20,39,120); border-radius: 6px; }
QLabel#rollValue { color: #aab5ca; font-size: 10px; }
QLabel#gainValue { color: #80e4a6; font-size: 11px; font-weight: 750; min-width: 52px; }
QLabel#projectedValue { color: #ffd484; font-size: 11px; font-weight: 750; min-width: 45px; }
QLabel#rowName { color: #e3e3ef; font-size: 12px; }
QLabel#rowValue { color: #ffffff; font-size: 12px; font-weight: 650; }
QLabel#relicSub { color: #e3e3ef; font-size: 9px; }
QLabel#relicSubValue { color: #ffffff; font-size: 9px; font-weight: 600; }
QLabel#upgradeBadge {
    color: #ffd278; background-color: rgba(30,24,48,150); border: 1px solid #8f7446;
    border-radius: 5px; padding: 0 3px; font-size: 8px; font-weight: 800;
}
QLabel#relicMainValue { color: #ffd1f2; font-size: 13px; font-weight: 750; }
QLabel#relicSlot { color: #ffffff; font-size: 10px; font-weight: 750; }
QLabel#relicSet { color: #d7d2e8; font-size: 9px; }
QFrame#relicScoreBand {
    background-color: rgba(10,17,32,105); border: 1px solid rgba(196,211,239,35);
    border-radius: 7px;
}
QLabel#relicScoreLabel {
    color: #b9c6dc; border: none; font-size: 9px; font-weight: 750;
}
QLabel#relicScoreValue {
    color: #f4f7ff; background-color: #263550; border: 1px solid #425573;
    border-radius: 7px; padding: 3px 7px; font-size: 10px; font-weight: 850;
}
QLabel#relicScoreValue[scoreTier="f"] {
    color: #ffc0c0; background-color: #48232c; border-color: #813946;
}
QLabel#relicScoreValue[scoreTier="fplus"] {
    color: #ffc7b8; background-color: #55282b; border-color: #945044;
}
QLabel#relicScoreValue[scoreTier="d"] {
    color: #ffd0a8; background-color: #4b3023; border-color: #855138;
}
QLabel#relicScoreValue[scoreTier="dplus"] {
    color: #ffdaa1; background-color: #573821; border-color: #97633a;
}
QLabel#relicScoreValue[scoreTier="c"] {
    color: #ffe29b; background-color: #493d20; border-color: #7e6931;
}
QLabel#relicScoreValue[scoreTier="cplus"] {
    color: #f1e99d; background-color: #4a4621; border-color: #85813a;
}
QLabel#relicScoreValue[scoreTier="b"] {
    color: #e9f2a4; background-color: #374321; border-color: #63783c;
}
QLabel#relicScoreValue[scoreTier="bplus"] {
    color: #d2f3a8; background-color: #304a26; border-color: #5d8844;
}
QLabel#relicScoreValue[scoreTier="a"] {
    color: #adf0bf; background-color: #1f4430; border-color: #3b7b55;
}
QLabel#relicScoreValue[scoreTier="aplus"] {
    color: #a7f2dc; background-color: #1c4940; border-color: #398779;
}
QLabel#relicScoreValue[scoreTier="s"] {
    color: #a8ecf3; background-color: #1c4149; border-color: #397782;
}
QLabel#relicScoreValue[scoreTier="splus"] {
    color: #a9e7ff; background-color: #1b4054; border-color: #3986a4;
}
QLabel#relicScoreValue[scoreTier="ss"] {
    color: #acd8ff; background-color: #203c5b; border-color: #3e70a0;
}
QLabel#relicScoreValue[scoreTier="ssplus"] {
    color: #b9cbff; background-color: #29395f; border-color: #526fae;
}
QLabel#relicScoreValue[scoreTier="sss"] {
    color: #d1c0ff; background-color: #342c5a; border-color: #6757a1;
}
QLabel#relicScoreValue[scoreTier="sssplus"] {
    color: #e5bcff; background-color: #432a5c; border-color: #8053a5;
}
QLabel#relicScoreValue[scoreTier="wtf"] {
    color: #ffc0f1; background-color: #512b52; border-color: #925092;
}
QLabel#relicScoreValue[scoreTier="wtfplus"] {
    color: #ffd0df; background-color: #5a2945; border-color: #a55178;
}
QLabel#relicScoreValue[scoreTier="aeon"] {
    color: #ffe5a3; background-color: #54401e; border-color: #a47c32;
}
QLabel#relicHolderCurrent, QLabel#relicHolderPrevious {
    border-radius: 5px; padding: 3px 6px; font-size: 9px; font-weight: 750;
}
QLabel#relicHolderCurrent {
    color: #a9f0ca; background-color: #173b36; border: 1px solid #326c5e;
}
QLabel#relicHolderPrevious {
    color: #b9c6db; background-color: #202d42; border: 1px solid #3b4b65;
}
QLabel#relicInventoryTitle {
    color: #f4f7ff; font-size: 21px; font-weight: 850;
}
QFrame#relicFilterPanel {
    background-color: #141f35; border: 1px solid #2f4262; border-radius: 9px;
}
QFrame#relicFilterPanel QComboBox {
    min-height: 26px; background-color: #0f192b; border-color: #385174;
}
QLabel#relicResultCount {
    color: #91a6c6; font-size: 10px; font-weight: 700; padding: 0 4px;
}
QScrollArea#relicInventoryScroll { background-color: transparent; border: none; }
QLabel#relicInventoryEmpty {
    color: #8290aa; font-size: 13px; padding: 60px;
}
QLabel#portraitName { color: #d9dceb; font-size: 10px; font-weight: 650; }
QLabel#artCaption {
    color: #ffffff; background-color: rgba(15,17,34,185); border-radius: 7px;
    padding: 6px 9px; font-size: 13px; font-weight: 700;
}
QListWidget#portraitList { min-height: 102px; max-height: 102px; }
QListWidget#portraitList::item { margin: 3px; border-radius: 8px; }
QListWidget#portraitList::item:selected { background-color: #584b79; border: 1px solid #efc8f2; }
QFrame#sideBar {
    background-color: #0d1322; border: 1px solid #27334d; border-radius: 10px;
}
QFrame#sidebarUserPanel {
    background-color: #131f34; border: 1px solid #304564; border-radius: 9px;
}
QLabel#sidebarAvatar, QLabel#settingsAvatar {
    color: #e8f8ff; background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #278fc0, stop:1 #7658c5);
    border: 1px solid #75c9ec; border-radius: 17px; font-weight: 850;
}
QLabel#settingsAvatar { border-radius: 29px; font-size: 22px; }
QLabel#sidebarUsername { color: #f4f7ff; font-size: 11px; font-weight: 750; }
QLabel#sidebarUserStatus { color: #74849d; font-size: 9px; }
QLabel#sideBrand { color: #ffffff; font-size: 19px; font-weight: 800; }
QLabel#sideSection { color: #77849b; font-size: 10px; font-weight: 750; }
QPushButton#sidebarToggle, QPushButton#navButton, QPushButton#authButton {
    background-color: transparent; color: #b8c4d8; border: none;
    border-radius: 8px; padding: 9px; text-align: left; font-weight: 650;
}
QPushButton#navButton { padding: 7px 9px; }
QPushButton#authButton { background-color: #152238; border: 1px solid #30445f; color: #8edfff; }
QPushButton#settingsButton {
    background-color: transparent; color: #9ecfe8; border: none;
    border-radius: 7px; font-size: 17px;
}
QPushButton#settingsButton:hover { background-color: #263b59; color: #ffffff; }
QPushButton#sidebarToggle { color: #7ed9ff; font-size: 18px; text-align: center; }
QPushButton#sidebarToggle:hover, QPushButton#navButton:hover, QPushButton#authButton:hover { background-color: #182f4b; color: #ffffff; }
QPushButton#navButton:checked { background-color: #213450; color: #8ee0ff; }
QScrollArea#whatsNewScroll, QWidget#whatsNewPage, QWidget#whatsNewContent {
    background-color: transparent; border: none;
}
QFrame#whatsNewHero {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #122844, stop:0.55 #202449, stop:1 #482650);
    border: 1px solid #526f9b; border-radius: 16px;
}
QLabel#whatsNewBadge {
    color: #8ee5ff; font-size: 10px; font-weight: 900;
    letter-spacing: 1px;
}
QLabel#whatsNewHeadline {
    color: #ffffff; font-size: 23px; font-weight: 900;
}
QLabel#whatsNewSummary {
    color: #b2c6e0; font-size: 12px;
}
QLabel#whatsNewFact {
    color: #bcecff; background-color: rgba(18,54,82,175);
    border: 1px solid #43769a; border-radius: 7px;
    padding: 5px 8px; font-size: 9px; font-weight: 850;
}
QLabel#whatsNewHeroImage {
    border: 1px solid #6585ac; border-radius: 12px;
    background-color: #0c1729;
}
QFrame#releaseFeatureCard {
    background-color: #111d31; border: 1px solid #304969;
    border-radius: 13px;
}
QFrame#releaseFeatureCard:hover {
    background-color: #14243b; border-color: #4d7097;
}
QLabel#releaseFeatureArtwork {
    background-color: #0d1728; border: 1px solid #304c70;
    border-radius: 11px;
}
QLabel#releaseFeatureTitle {
    color: #f4f8ff; font-size: 16px; font-weight: 850;
}
QLabel#releaseFeatureCategory {
    color: #72d9f4; font-size: 9px; font-weight: 900;
    letter-spacing: 1px;
}
QLabel#releaseFeatureDescription {
    color: #aabbd2; font-size: 11px;
}
QLabel#releaseFeatureDetail {
    color: #bed0e5; font-size: 10px; padding: 1px 0;
}
QPushButton#releaseFeatureButton {
    color: #eafaff; background-color: #1b4665;
    border: 1px solid #4fa7ca; border-radius: 8px;
    padding: 9px 12px; font-weight: 800;
}
QPushButton#releaseFeatureButton:hover {
    background-color: #246486; border-color: #75d9f4;
}
QDialog#authDialog { background-color: transparent; }
QFrame#authModal {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #101a2d, stop:1 #1b1838);
    border: 1px solid #41577d; border-radius: 13px;
}
QFrame#loginErrorFlash {
    background-color: rgba(255,45,76,52);
    border: 2px solid rgba(255,91,115,205);
    border-radius: 13px;
}
QFrame#authModal[loginError="true"] {
    border: 2px solid #f05a70;
}
QDialog#settingsDialog { background-color: transparent; }
QFrame#settingsModal {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #0d1728, stop:0.62 #121b30, stop:1 #21172f);
    border: 1px solid #4b6085; border-radius: 15px;
}
QFrame#settingsSidebar {
    background-color: #0b1424; border: none; border-right: 1px solid #2b3e5b;
    border-bottom-left-radius: 14px;
}
QWidget#settingsContent, QWidget#settingsPage, QStackedWidget#settingsStack {
    background-color: transparent; border: none;
}
QPushButton#settingsNavButton {
    color: #899bb5; background-color: transparent; border: none;
    border-radius: 8px; padding: 10px 11px; text-align: left; font-weight: 750;
}
QPushButton#settingsNavButton:hover {
    color: #edf7ff; background-color: #162640;
}
QPushButton#settingsNavButton:checked {
    color: #9fe7ff; background-color: #1b3554; border-left: 3px solid #66caed;
}
QLabel#settingsSidebarUser {
    color: #7387a5; border-top: 1px solid #263a56; padding: 12px 5px 2px 5px;
    font-size: 10px; font-weight: 700;
}
QLabel#settingsPageTitle { color: #ffffff; font-size: 19px; font-weight: 900; }
QLabel#settingsPageSubtitle { color: #8499b7; font-size: 11px; }
QComboBox#settingsThemeSelector {
    min-height: 26px; padding: 8px 11px; font-size: 12px; font-weight: 750;
}
QDialog#authDialog QLineEdit[invalid="true"] {
    color: #fff1f3; background-color: #321521;
    border: 1px solid #ff5f76;
    selection-background-color: #a8394c;
}
QDialog#rankRedirectDialog { background-color: transparent; }
QDialog#buildComparisonDialog { color: #eaf1ff; background-color: transparent; }
QFrame#buildComparisonModal {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #091322, stop:0.58 #101a2e, stop:1 #20172f);
    border: 1px solid #50698f; border-radius: 16px;
}
QFrame#buildComparisonHeader {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #162a45, stop:0.6 #17213c, stop:1 #2a1c42);
    border: 1px solid #3d587c; border-radius: 11px;
}
QLabel#buildComparisonIcon {
    color: #a8ecff; background-color: #173b58; border: 1px solid #4b9fc4;
    border-radius: 19px; font-size: 19px; font-weight: 900;
}
QDialog#buildDeleteDialog { background-color: transparent; }
QFrame#buildDeleteCard {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #111c30, stop:1 #24182d);
    border: 1px solid #75465d; border-radius: 13px;
}
QLabel#buildDeleteTitle { color: #ffb0ba; font-size: 15px; font-weight: 850; }
QLabel#buildDeleteMessage { color: #c8d2e2; font-size: 11px; }
QLabel#buildComparisonTitle { color: #ffffff; font-size: 17px; font-weight: 850; }
QLabel#buildComparisonSubtitle { color: #8fa8c8; font-size: 10px; }
QFrame#buildComparisonSummary {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #121f35, stop:0.5 #172540, stop:1 #201d3d);
    border: 1px solid #3a557b; border-radius: 12px;
}
QLabel#buildComparisonMetricLabel { color: #8499b8; font-size: 9px; font-weight: 800; }
QLabel#buildComparisonMetric {
    color: #edf4ff; font-size: 19px; font-weight: 850; padding: 4px;
}
QLabel#buildComparisonMetric[metricType="old"] { color: #b9c9e3; }
QLabel#buildComparisonMetric[metricType="gain"] { color: #88e8ad; }
QLabel#buildComparisonMetric[metricType="loss"] { color: #ff8795; }
QLabel#buildComparisonMetric[metricType="equal"] { color: #8996aa; }
QLabel#buildComparisonMetric[metricType="new"] { color: #8edfff; }
QLabel#buildComparisonCone, QLabel#buildComparisonTeam, QLabel#buildComparisonRelics {
    color: #cfdaec; background-color: #101c30; border: 1px solid #304968;
    border-radius: 9px; padding: 10px 12px; font-size: 10px; font-weight: 700;
}
QLabel#buildComparisonTeam { color: #9edfff; }
QTableWidget#buildComparisonTable {
    color: #e8eef9; background-color: #101a2d; alternate-background-color: #142139;
    border: 1px solid #3a5277; border-radius: 10px; gridline-color: transparent;
}
QTableWidget#buildComparisonTable::item {
    padding: 7px; border-bottom: 1px solid #213553;
}
QTableWidget#buildComparisonTable QHeaderView::section {
    color: #bed0e8; background-color: #192944; border: none;
    border-right: 1px solid #344b6e; padding: 8px; font-size: 10px; font-weight: 800;
}
QFrame#rankRedirectModal {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #121e33, stop:0.58 #17213b, stop:1 #281d43);
    border: 1px solid #506d94; border-radius: 15px;
}
QLabel#rankRedirectIcon {
    color: #ffe18b; background-color: #3b3022; border: 1px solid #76613b;
    border-radius: 19px; font-size: 17px; font-weight: 850;
}
QLabel#rankRedirectMessage {
    color: #dbe5f3; font-size: 13px; padding: 5px 8px;
}
QLabel#rankRedirectUid {
    color: #9be7ff; background-color: #0d192b; border: 1px solid #3c6385;
    border-radius: 10px; padding: 10px; font-size: 18px;
    font-weight: 850; letter-spacing: 2px;
}
QPushButton#dialogCloseButton {
    background-color: transparent; color: #aab7cb; border: none;
    border-radius: 7px; font-size: 18px;
}
QPushButton#dialogCloseButton:hover { background-color: #c94f68; color: white; }
QPushButton#authTabButton {
    background-color: #111b2e; color: #8493aa; border: 1px solid #293a57;
    border-radius: 8px; padding: 8px; font-weight: 700;
}
QPushButton#authTabButton:checked {
    background-color: #213b5c; color: #92e2ff; border-color: #4c83aa;
}
QLabel#authMessage { color: #ff9b9b; font-size: 11px; min-height: 20px; }
QPushButton#dangerButton {
    background-color: #3a1c2a; color: #ffacb9; border: 1px solid #713447;
    border-radius: 9px; padding: 10px; font-weight: 750;
}
QPushButton#dangerButton:hover { background-color: #572337; color: #ffffff; }
QLabel#plannerTitle {
    color: #8fc0ff; font-size: 22px; font-weight: 800;
    text-decoration: underline; padding: 6px 0 8px 0;
}
QScrollArea#plannerScroll { background-color: transparent; border: none; }
QFrame#plannerSettingsCard {
    background-color: #20375f; border: 1px solid #4c73aa; border-radius: 7px;
}
QLabel#plannerColumnTitle {
    color: #f3f7ff; font-size: 13px; font-weight: 850; padding-bottom: 2px;
}
QComboBox#plannerStrategySelect {
    color: #eef5ff; background-color: #172c4b; border: 1px solid #4779bc;
    border-radius: 6px; padding: 7px 11px; min-height: 22px; font-weight: 700;
}
QComboBox#plannerStrategySelect:hover,
QComboBox#plannerStrategySelect:focus,
QComboBox#plannerStrategySelect:on {
    background-color: #1c365c; border-color: #65a7ef;
}
QLabel#plannerResourceIcon {
    background-color: #152947; border: 1px solid #3c608c;
    border-radius: 9px;
}
QSpinBox#plannerResourceSpin {
    min-height: 20px; padding: 6px 10px;
}
QLabel#plannerPityValue, QLabel#plannerGuarantee {
    color: #eef5ff; background-color: #192d4e; border: 1px solid #355783;
    border-radius: 4px; min-height: 24px; padding: 2px 7px;
}
QLabel#plannerGuarantee[guaranteed="true"] {
    color: #8ff0b2; background-color: #183d35; border-color: #3a8167;
}
QLabel#plannerGuarantee[guaranteed="false"] {
    color: #f0b3c0; background-color: #3c2335; border-color: #71435d;
}
QLabel#plannerResourcesLine {
    color: #a8cfff; border-bottom: 1px solid #36577e;
    padding: 8px 12px; font-size: 12px; font-weight: 700;
}
QTableWidget#plannerGoalTable {
    background-color: #20375f; color: #f2f6ff; border: 1px solid #466b9d;
    border-radius: 5px; gridline-color: #45648d; alternate-background-color: #1b3155;
}
QTableWidget#plannerGoalTable::item {
    border-bottom: 1px solid #45648d; padding: 5px;
}
QTableWidget#plannerGoalTable QHeaderView::section {
    background-color: #172b4b; color: #f2f6ff; border: none;
    border-bottom: 1px solid #45648d; padding: 8px; font-weight: 800;
}
QTableWidget#plannerGoalTable QProgressBar {
    color: #ffffff; background-color: #172a49; border: none;
    border-radius: 3px; text-align: center; font-weight: 800;
}
QProgressBar[chanceLevel="high"]::chunk { background-color: #69bb75; border-radius: 3px; }
QProgressBar[chanceLevel="medium"]::chunk { background-color: #a8bf59; border-radius: 3px; }
QProgressBar[chanceLevel="low"]::chunk { background-color: #d0944c; border-radius: 3px; }
QProgressBar[chanceLevel="critical"]::chunk { background-color: #c34f4f; border-radius: 3px; }
QWidget#catalogPage, QWidget#catalogGridContent, QWidget#catalogDetailContent {
    background-color: #080d19;
}
QLabel#catalogTitle {
    color: #f4f7ff; font-size: 21px; font-weight: 850;
}
QFrame#catalogControls {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #101b2e, stop:0.55 #142039, stop:1 #1d1935);
    border: 1px solid #334968; border-radius: 12px;
}
QPushButton#catalogTabButton {
    color: #91a2bd; background-color: #0d1728; border: 1px solid #293d5c;
    border-radius: 7px; padding: 8px 14px; font-weight: 750;
}
QPushButton#catalogTabButton:hover { color: #ffffff; background-color: #1b3150; }
QPushButton#catalogTabButton:checked {
    color: #9ce8ff; background-color: #234463; border-color: #4d88ad;
}
QLineEdit#catalogSearch {
    color: #edf5ff; background-color: #0d1728; border: 1px solid #304a6d;
    border-radius: 8px; padding: 8px 11px; selection-background-color: #32658b;
}
QLineEdit#catalogSearch:focus { border-color: #67bde8; }
QLabel#catalogResultCount {
    color: #9eddf3; background-color: #10263b; border: 1px solid #294b68;
    border-radius: 8px; font-size: 10px; font-weight: 800; padding: 5px 9px;
}
QScrollArea#catalogScroll, QScrollArea#catalogDetailScroll {
    background-color: transparent; border: none;
}
QFrame#catalogCard {
    background-color: #101a2d; border: 1px solid #304563; border-radius: 12px;
}
QFrame#catalogCard:hover {
    background-color: #172a45; border-color: #6ec7e8;
}
QFrame#catalogCardArt {
    background-color: #091221; border: none;
    border-top-left-radius: 11px; border-top-right-radius: 11px;
}
QLabel#catalogCardImage {
    color: #607492; background-color: #091221;
    border-top-left-radius: 11px; border-top-right-radius: 11px; font-size: 30px;
}
QLabel#catalogCardKind, QLabel#catalogCardRarity {
    margin: 7px; padding: 3px 6px; border-radius: 6px;
    background-color: rgba(6,11,21,205); border: 1px solid rgba(207,222,247,55);
    font-size: 8px; font-weight: 900;
}
QLabel#catalogCardKind { color: #87dff8; letter-spacing: 1px; }
QLabel#catalogCardRarity { color: #ffd56c; }
QFrame#catalogCardFooter {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #101b2f, stop:1 #171a35);
    border: none; border-bottom-left-radius: 11px; border-bottom-right-radius: 11px;
}
QLabel#catalogCardName { color: #f5f8ff; font-size: 11px; font-weight: 850; }
QLabel#catalogCardMeta { color: #9babc1; font-size: 9px; font-weight: 700; }
QLabel#catalogCardMetaIcon {
    background-color: rgba(35,51,78,190); border: 1px solid #3b5678;
    border-radius: 9px;
}
QLabel#catalogStars, QLabel#catalogDetailStars { color: #ffd66b; font-weight: 800; }
QLabel#catalogEmpty { color: #8290aa; font-size: 13px; padding: 60px; }
QPushButton#catalogBackButton {
    color: #9cddf5; background-color: #14243a; border: 1px solid #304e6e;
    border-radius: 8px; padding: 8px 13px; font-weight: 750;
}
QPushButton#catalogBackButton:hover { color: #ffffff; background-color: #203b5b; }
QFrame#catalogHero {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #172844, stop:0.58 #1e2948, stop:1 #342143);
    border: 1px solid #3f567d; border-radius: 12px;
}
QLabel#catalogHeroImage { color: #71829c; background-color: #0b1322; border-radius: 9px; }
QLabel#catalogConeHeroImage {
    color: #71829c; background-color: #080f1d; border: 1px solid #4b6388;
    border-radius: 6px;
}
QFrame#characterAnalysisPanel {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #101d32, stop:0.58 #172743, stop:1 #34213e);
    border: 1px solid #496184; border-radius: 14px;
}
QLabel#characterAnalysisArt {
    color: #71829c; background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #14223a, stop:1 #0a111f);
    border: 1px solid #577196; border-radius: 10px; font-size: 34px;
}
QLabel#characterAnalysisEyebrow {
    color: #7bdcff; font-size: 10px; font-weight: 900; letter-spacing: 1px;
}
QFrame#characterIdentityChip {
    background-color: rgba(19,38,61,210); border: 1px solid #3f6487;
    border-radius: 9px;
}
QLabel#characterIdentityChipText {
    color: #dcecff; font-size: 10px; font-weight: 800;
}
QLabel#characterSummaryBadge {
    color: #aabbd2; background-color: rgba(9,18,32,180);
    border: 1px solid #314966; border-radius: 6px;
    padding: 4px 7px; font-size: 8px; font-weight: 800;
}
QFrame#characterInfoSection {
    background-color: #0e182a; border: 1px solid #2e4362; border-radius: 12px;
}
QFrame#characterInfoSection[collapsed="true"] {
    background-color: #0c1626; border-color: #263b58;
}
QLabel#characterSectionTitle {
    color: #f1f6ff; font-size: 15px; font-weight: 900; letter-spacing: 1px;
}
QLabel#characterSectionHint { color: #8297b5; font-size: 10px; }
QLabel#characterSectionCount {
    color: #9be5ff; background-color: #17334d; border: 1px solid #35617f;
    border-radius: 10px; padding: 4px 9px; font-size: 9px; font-weight: 900;
}
QPushButton#characterSectionToggle {
    color: #9fdff5; background-color: #132a42; border: 1px solid #315a79;
    border-radius: 8px; padding: 5px 10px; font-size: 9px; font-weight: 850;
}
QPushButton#characterSectionToggle:hover {
    color: #ffffff; background-color: #1b3b59; border-color: #4d83a7;
}
QFrame#characterDetailTabBar {
    background-color: #0b1424; border: 1px solid #2b405e; border-radius: 11px;
}
QPushButton#characterDetailTab {
    min-height: 30px; color: #8fa3c0; background-color: transparent;
    border: 1px solid transparent; border-radius: 7px; font-size: 10px;
    font-weight: 850;
}
QPushButton#characterDetailTab:hover {
    color: #dff7ff; background-color: #132740; border-color: #294c6b;
}
QPushButton#characterDetailTab:checked {
    color: #ffffff; background-color: #1b4968; border-color: #55a4cc;
}
QFrame#coneAnalysisPanel {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #101d32, stop:0.58 #17233d, stop:1 #2a1d3a);
    border: 1px solid #415b83; border-radius: 13px;
}
QLabel#coneAnalysisArt {
    color: #71829c; background-color: #070d18; border: 1px solid #6680a6;
    border-radius: 7px;
}
QLabel#coneAnalysisCaption {
    color: #7186a6; font-size: 9px; font-weight: 800; letter-spacing: 1px;
}
QLabel#coneAnalysisEyebrow {
    color: #79d8ff; font-size: 10px; font-weight: 900; letter-spacing: 1px;
}
QPushButton#coneRankButton {
    min-height: 28px; color: #9cacbf; background-color: #0c1627;
    border: 1px solid #304663; border-radius: 7px; font-weight: 850;
}
QPushButton#coneRankButton:hover {
    color: #ffffff; background-color: #213958; border-color: #5989ae;
}
QPushButton#coneRankButton:checked {
    color: #201508; background-color: #ffad5c; border-color: #ffd18d;
}
QFrame#coneEffectAnalysisCard {
    background-color: #0c1729; border: 1px solid #354f72; border-radius: 9px;
}
QLabel#coneEffectTitle {
    color: #f5f7ff; font-size: 13px; font-weight: 900;
}
QFrame#coneProgressCard {
    background-color: #0b1525; border: 1px solid #293d59; border-radius: 7px;
}
QFrame#coneProgressCard[selected="true"] {
    background-color: #392a1d; border-color: #d88b43;
}
QLabel#coneProgressStage {
    color: #8fa5c4; font-size: 9px; font-weight: 850;
}
QLabel#coneProgressValues {
    color: #ffad5c; font-size: 10px; font-weight: 900;
}
QLabel#catalogDetailName { color: #ffffff; font-size: 25px; font-weight: 900; }
QLabel#catalogDetailStars { font-size: 17px; }
QLabel#catalogDetailMeta { color: #a8bad2; font-size: 13px; }
QFrame#catalogStatsCard, QFrame#catalogInfoCard, QFrame#catalogEffectCard {
    background-color: #111c30; border: 1px solid #2d4262; border-radius: 10px;
}
QFrame#catalogInfoCard:hover { background-color: #15243a; border-color: #426486; }
QLabel#catalogStatName { color: #8094b1; font-size: 10px; font-weight: 750; }
QLabel#catalogStatValue { color: #86e1ff; font-size: 18px; font-weight: 850; }
QLabel#catalogSectionTitle {
    color: #dce8fa; font-size: 14px; font-weight: 850; padding: 6px 2px 2px 2px;
}
QLabel#catalogInfoBadge {
    color: #a9e9ff; background-color: #172e49; border: 1px solid #426b8c;
    border-radius: 10px; font-size: 10px; font-weight: 850;
}
QLabel#catalogInfoKind {
    color: #77d8f6; background-color: #142c45; border: 1px solid #315b7b;
    border-radius: 5px; padding: 2px 6px; font-size: 8px; font-weight: 900;
}
QLabel#catalogInfoTitle { color: #f2f6ff; font-size: 12px; font-weight: 850; }
QLabel#catalogInfoText { color: #bdcbe0; font-size: 11px; line-height: 1.25; }
QLabel#catalogLore {
    color: #9cacc3; background-color: #0d1728; border-left: 2px solid #526f98;
    padding: 11px 13px; font-style: italic;
}
QFrame#statusBar { background-color: transparent; border: none; }
QPushButton#copyErrorButton {
    color: #ffc0ca; background-color: #321b27; border: 1px solid #7c4154;
    border-radius: 7px; padding: 6px 10px; font-size: 10px; font-weight: 800;
}
QPushButton#copyErrorButton:hover {
    color: #ffffff; background-color: #512536; border-color: #c76780;
}
QDialog#experienceDialog, QDialog#tutorialDialog { background-color: transparent; }
QWidget#guidedTourOverlay { background-color: transparent; }
QFrame#tourBalloon {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #0d182a, stop:0.62 #17243b, stop:1 #271d3b);
    border: 2px solid #58cbed; border-radius: 14px;
}
QLabel#tourCounter {
    color: #7bdcff; font-size: 9px; font-weight: 900; letter-spacing: 1px;
}
QLabel#tourTitle { color: #ffffff; font-size: 18px; font-weight: 900; }
QLabel#tourText { color: #bccce2; font-size: 11px; line-height: 1.3; }
QPushButton#tourSkipButton {
    color: #93a5be; background-color: transparent; border: none;
    padding: 8px 4px; font-weight: 700;
}
QPushButton#tourSkipButton:hover { color: #ffffff; text-decoration: underline; }
QWidget#diagnosticsPage { background-color: #080d19; }
QPushButton#subtleButton {
    color: #93a5be; background-color: transparent; border: 1px solid #35445d;
    border-radius: 8px; padding: 8px 12px; font-weight: 700;
}
QPushButton#subtleButton:hover {
    color: #ffffff; background-color: #17243a; border-color: #526b8e;
}
QCheckBox#experienceCheckBox {
    color: #edf4ff; background-color: #111e32; border: 1px solid #334d70;
    border-radius: 9px; padding: 11px; font-weight: 700;
}
QFrame#tutorialCard {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #0d182a, stop:0.58 #172039, stop:1 #2a1b3c);
    border: 1px solid #66538d; border-radius: 18px;
}
QLabel#tutorialIcon {
    color: #8bdfff; font-size: 34px; font-weight: 900;
}
QLabel#tutorialTitle {
    color: #ffffff; font-size: 22px; font-weight: 900;
}
QLabel#tutorialText {
    color: #bccae0; font-size: 12px; padding: 4px 28px;
}
QLabel#tutorialSteps { color: #8dcde9; font-size: 13px; }
QLabel#diagnosticsSummary {
    color: #cbd9eb; background-color: #0c1626; border: 1px solid #314967;
    border-radius: 12px; padding: 18px; font-family: "Consolas", "Cascadia Mono";
    font-size: 11px;
}
QFrame#updateInstallWarning {
    background-color: #2d2418; border: 1px solid #8d6735; border-radius: 9px;
}
QLabel#updateWarningIcon {
    color: #171006; background-color: #ffbd62; border-radius: 12px;
    font-size: 14px; font-weight: 900;
}
QLabel#updateWarningText { color: #f4d6a7; font-size: 10px; }
QLabel#updateReadyWarning {
    color: #ffe1ae; background-color: #302316; border: 1px solid #a87536;
    border-radius: 9px; padding: 12px; font-size: 11px; font-weight: 850;
}
"""

from app.visual_style import REFINED_STYLESHEET

APP_STYLESHEET += REFINED_STYLESHEET

APP_STYLESHEET += """
QFrame#uidQueryBar, QFrame#uidTabsPanel {
    background-color: #101d31;
    border: 1px solid #294563;
    border-radius: 10px;
}
QLabel#uidQueryLabel {
    color: #83dff5;
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 1px;
}
QLineEdit#uidQueryInput {
    min-height: 34px;
    padding: 0 11px;
    background-color: #0a1526;
    border: 1px solid #34577a;
    border-radius: 7px;
    color: #f3f8ff;
    selection-background-color: #2d8fbd;
}
QLineEdit#uidQueryInput:focus { border-color: #66d9f3; }
QPushButton#uidQueryButton, QPushButton#uidTabRefreshButton {
    min-height: 34px;
    padding: 0 13px;
    background-color: #173552;
    border: 1px solid #3f7194;
    border-radius: 7px;
    color: #eaf8ff;
    font-weight: 700;
}
QPushButton#uidQueryButton:hover, QPushButton#uidTabRefreshButton:hover {
    background-color: #204969;
    border-color: #6edcf2;
}
QTabBar#uidTabBar { background: transparent; }
QTabBar#uidTabBar::tab {
    min-width: 130px;
    max-width: 230px;
    min-height: 34px;
    padding: 3px 28px 3px 10px;
    margin-right: 4px;
    background-color: #0b1728;
    border: 1px solid #2b4663;
    border-radius: 8px;
    color: #9fb3c9;
}
QTabBar#uidTabBar::tab:selected {
    background-color: #173451;
    border-color: #63d6ef;
    color: #ffffff;
}
QTabBar#uidTabBar::tab:hover:!selected {
    background-color: #13263d;
    color: #d8e9f5;
}
QTabBar#uidTabBar QToolButton {
    border: none;
    background: transparent;
    color: #9fb3c9;
}
QLabel#uidTabMeta {
    color: #8097b2;
    font-size: 10px;
    padding-left: 3px;
}
QLabel#uidTabMeta[state="loading"] { color: #71dff5; }
QLabel#uidTabMeta[state="error"] { color: #ff9f9f; }
QLabel#uidTabMeta[state="ready"] { color: #8ccfb7; }
QFrame#enkaRecoveryPanel {
    background-color: #171b2c;
    border: 1px solid #8c5260;
    border-radius: 10px;
}
QLabel#enkaRecoveryIcon {
    background-color: #382132;
    border: 1px solid #cf7180;
    border-radius: 17px;
    color: #ff9eaa;
    font-size: 17px;
    font-weight: 900;
}
QLabel#enkaRecoveryTitle {
    color: #fff4f5;
    font-size: 13px;
    font-weight: 800;
}
QLabel#enkaRecoveryCategory {
    padding: 2px 7px;
    background-color: #342033;
    border: 1px solid #75465b;
    border-radius: 7px;
    color: #ef9eae;
    font-size: 9px;
    font-weight: 800;
}
QLabel#enkaRecoveryMessage {
    color: #c8d2df;
    font-size: 11px;
}
QPushButton#enkaRecoveryAction {
    min-height: 28px;
    padding: 0 10px;
    background-color: #202a3d;
    border: 1px solid #45566f;
    border-radius: 6px;
    color: #e5edf7;
    font-size: 10px;
    font-weight: 700;
}
QPushButton#enkaRecoveryAction:hover {
    background-color: #2a3950;
    border-color: #76cce2;
    color: #ffffff;
}
"""
