# -*- mode: python ; coding: utf-8 -*-

import os
from pathlib import Path

from PyInstaller.building.build_main import Analysis, EXE, PYZ
from PyInstaller.utils.hooks import collect_data_files
block_cipher = None
SPEC_DIR = Path(__file__).parent if "__file__" in globals() else Path.cwd()

datas = [
    (str(SPEC_DIR / "app" / "assets"), "app/assets"),
    (str(SPEC_DIR / "app" / "data"), "app/data"),
    (str(SPEC_DIR / "assets" / "icon.ico"), "assets"),
]
datas += collect_data_files("certifi")

a = Analysis(
    [str(SPEC_DIR / "start_app.py")],
    pathex=[str(SPEC_DIR)],
    binaries=[],
    datas=datas,
    hiddenimports=["imageio_ffmpeg"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "tests"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="EditorVideoApp",
    icon=str(SPEC_DIR / "assets" / "icon.ico"),
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=os.environ.get("EDITOR_VIDEO_CONSOLE") == "1",
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
