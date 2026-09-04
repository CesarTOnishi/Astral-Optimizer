from pathlib import Path
import shutil

from PyInstaller.utils.hooks import collect_all, collect_submodules


ROOT = Path(SPECPATH)
FRIBBELS = ROOT / "third_party" / "fribbels-hsr-optimizer"
ASSETS = FRIBBELS / "public" / "assets"

datas = [
    (str(ROOT / "app" / "assets"), "app/assets"),
    (str(ROOT / "app" / "benchmark" / "fribbels_teams.json"), "app/benchmark"),
    (str(ROOT / "app" / "benchmark" / "fribbels_weights.json"), "app/benchmark"),
    (str(FRIBBELS / "src" / "data" / "game_data.json"),
     "third_party/fribbels-hsr-optimizer/src/data"),
    (str(FRIBBELS / "package.json"), "third_party/fribbels-hsr-optimizer"),
    (str(FRIBBELS / "public" / "locales" / "pt_BR" / "gameData.yaml"),
     "third_party/fribbels-hsr-optimizer/public/locales/pt_BR"),
    (str(FRIBBELS / ".honkai-engine" / "benchmark-engine.js"),
     "third_party/fribbels-hsr-optimizer/.honkai-engine"),
    (str(ASSETS / "icon"), "third_party/fribbels-hsr-optimizer/public/assets/icon"),
    (str(ASSETS / "image" / "character_preview"),
     "third_party/fribbels-hsr-optimizer/public/assets/image/character_preview"),
    (str(ASSETS / "image" / "character_portrait"),
     "third_party/fribbels-hsr-optimizer/public/assets/image/character_portrait"),
    (str(ASSETS / "image" / "light_cone_portrait"),
     "third_party/fribbels-hsr-optimizer/public/assets/image/light_cone_portrait"),
]
datas.extend(
    (str(path), "third_party/fribbels-hsr-optimizer/public/assets/misc")
    for path in (ASSETS / "misc").glob("*")
    if path.is_file()
)

enka_datas, enka_binaries, enka_hidden = collect_all("enka")
datas.extend(enka_datas)

node = shutil.which("node")
if not node:
    raise SystemExit("Node.js não encontrado. Instale-o antes de criar o executável.")

binaries = [(node, "runtime"), *enka_binaries]
hiddenimports = [
    *enka_hidden,
    *collect_submodules("google_auth_oauthlib"),
    *collect_submodules("googleapiclient"),
    *collect_submodules("keyring.backends"),
]

a = Analysis(
    [str(ROOT / "honkai.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "tkinter"],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="AstralOptimizer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / "app" / "assets" / "astral_optimizer.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="AstralOptimizer",
)
