import sys
from cx_Freeze import setup, Executable

# Dependencies are automatically detected, but it might need fine-tuning.
build_exe_options = {
    "packages": ["PyQt6", "numpy", "soundfile", "timecode", "cffi"],
    "excludes": ["tkinter", "PyQt6.QtSql", "PyQt6.QtDesigner", "PyQt6.QtQml", "PyQt6.QtBluetooth"],
    "include_files": [
        "libltc.11.dylib",
        ("ltc_wrapper.cpython-313-darwin.so", "ltc_wrapper.so"),
        ("img/ReatcMarkLOGOheader.png", "ReatcMarkLOGOheader.png")
    ]
}

# bdist_mac options
bdist_mac_options = {
    "iconfile": "img/icon/MakeIcon.icns",
    "bundle_name": "REAtcMARK",
    "plist_items": [
        ('CFBundleIconFile', 'icon.icns'),
        ('CFBundleIdentifier', 'com.kittenmittensinc.reatcmark')
    ]
}

# Base set to "Win32GUI" on Windows, "None" on other platforms
base = None
if sys.platform == "win32":
    base = "Win32GUI"

# Define the executable
executables = [
    Executable(
        "main.py",
        base=base,
        target_name="REAtcMARK"
    )
]

setup(
    name="REAtcMARK",
    version="1.0",
    description="SMPTE to Reaper Marker Converter",
    options={
        "build_exe": build_exe_options,
        "bdist_mac": bdist_mac_options,
    },
    executables=executables,
) 