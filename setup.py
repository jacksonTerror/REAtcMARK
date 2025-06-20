from setuptools import setup, Extension
import platform
import pybind11

# Universal build flags for macOS
extra_compile_args = []
extra_link_args = []
if platform.system() == 'Darwin':
    extra_compile_args = ['-arch', 'x86_64', '-arch', 'arm64']
    extra_link_args = ['-arch', 'x86_64', '-arch', 'arm64']

ltc_wrapper_extension = Extension(
    'ltc_wrapper',
    sources=['ltc_wrapper.cpp'],
    include_dirs=[
        '/opt/homebrew/include',
        pybind11.get_include()
    ],
    library_dirs=['/opt/homebrew/lib'],
    libraries=['ltc'],
    extra_compile_args=extra_compile_args,
    extra_link_args=extra_link_args
)

APP = ['main.py']
DATA_FILES = []
OPTIONS = {
    'argv_emulation': False,
    'iconfile': 'img/icon/MakeIcon.icns',
    'packages': ['PyQt6', 'soundfile', 'sounddevice', 'numpy', 'timecode', 'jaraco.text'],
    'excludes': ['tkinter', 'tcl'],
    'resources': ['img', 'libltc.11.dylib'],
    'plist': {
        'CFBundleName': 'REAtcMARK',
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleVersion': '1.0.0',
        'NSHumanReadableCopyright': 'Copyright © 2025 Simon Borg. All rights reserved.'
    }
}

setup(
    name='REAtcMARK',
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app', 'pybind11'],
    ext_modules=[ltc_wrapper_extension],
) 