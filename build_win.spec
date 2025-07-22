# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build specification for the Windows build of REAtcMARK.
Usage (run **from inside this REAtcMARK folder**):
    pyinstaller --noconfirm build_win.spec
This bundles the img/ folder and applies the multi-size Windows icon.
"""

import os
from PyInstaller.utils.hooks import collect_data_files
from PyInstaller.building.build_main import Analysis, PYZ, EXE, COLLECT

block_cipher = None

# ------------------------------------------------------------------
# Analysis – discover imports/resources relative to *this* directory
# ------------------------------------------------------------------

a = Analysis(
    ['main.py'],                  # entry-point lives in the same folder
    pathex=[os.path.abspath('.')],
    binaries=[],
    datas=[
        ('ffmpeg.exe', '.'),               # static ffmpeg only
    ],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# ------------------------------------------------------------------
# Executable definition – GUI app with custom icon
# ------------------------------------------------------------------

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='REAtcMARK',
    icon='app_icon.ico',          # icon file sits beside this spec
    debug=False,
    strip=False,
    upx=True,
    console=False,               # change to True to see a console window
    distpath='build',            # keep raw exe out of dist/ to avoid confusion
)

# ------------------------------------------------------------------
# Final onedir bundle – everything ends up in dist/REAtcMARK/
# ------------------------------------------------------------------

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name='REAtcMARK',
) 