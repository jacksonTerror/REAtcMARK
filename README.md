# REAtcMARK

**Simple way to take your multitrack's timecode file and convert it into marker data for Reaper.**

---

## Overview

REAtcMARK is a desktop utility for macOS that analyzes pre-recorded audio files (WAV or MP3) containing SMPTE timecode and generates marker data **specifically for Reaper**. It streamlines the process of turning timecode into Reaper marker CSVs, setlists, and detailed reports for your sessions.

---

## Features

- Detects SMPTE timecode in pre-recorded WAV or MP3 audio files
- **Generates Reaper-compatible marker CSVs**
- Produces detailed detection report and setlist
- Simple, guided UI for entering show metadata and selecting files
- Supports importing and editing existing marker lists


---

## System Requirements

- macOS 12+ (Monterey or later)
- Apple Silicon (M1/M2/M3) or Intel Mac (see below for build instructions)
- No additional dependencies required for end users (all libraries bundled)

---

## Installation & Build Instructions

### For End Users

Download the appropriate `.dmg` for your Mac (Apple Silicon or Intel), open it, and drag `REAtcMARK.app` to your Applications folder.

### For Developers / Building from Source

#### 1. Clone or copy the project folder to your Mac.

#### 2. Install dependencies (Homebrew, Python, libltc):

```sh
# Install Homebrew if you don't have it
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python 3.13 and libltc
brew install python@3.13 libltc
```

#### 3. Set up a virtual environment and install Python packages:

```sh
/usr/local/opt/python@3.13/bin/python3.13 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install pyqt6 numpy soundfile timecode cffi pybind11 cx_freeze
```

#### 4. Compile the C++ wrapper:

```sh
c++ -O3 -Wall -shared -std=c++11 -undefined dynamic_lookup \
-I/usr/local/include \
-I$(python -c "import pybind11; print(pybind11.get_include())") \
ltc_wrapper.cpp \
-L/usr/local/lib -lltc \
-o ltc_wrapper.cpython-313-darwin.so
```

#### 5. Build the app and DMG:

```sh
python setup_cx.py bdist_mac
./create_dmg.sh
```

The script will create a DMG named for your architecture (e.g., `REAtcMARK-AppleSilicon.dmg`).

---

## Usage

1. **Enter Show Metadata:** Set the date, artist, and city. This information is used for output filenames.
2. **Select SMPTE Audio File:** Choose your multitrack's timecode WAV or MP3 file.
3. **Create or Import Marker List:** Generate a new marker list or import an existing one.
4. **Choose Output Folder:** Select where to save your results.
5. **Process:** Click "Process" to generate your files.
6. **Load in Reaper:** Import the generated CSV into Reaper to see your markers.

### Output Files

- `YYYY.MM.DD_artist_city_detailed.txt` — Detection report
- `YYYY.MM.DD_artist_city_markers.csv` — Reaper marker CSV
- `YYYY.MM.DD_artist_city_setlist.txt` — Setlist

Example outputs:
```
SMPTE Detection Report
===================

Audio File: 2025.06.18_SMPTE-test.wav
Frame Rate: 30 fps

Detected Markers:
00:00:24:00 - marker 1
00:04:18:00 - marker 3
```

---

## Troubleshooting

- If you see a security warning on first launch, right-click the app and choose "Open."
- For Intel Macs, be sure to use the Intel-specific DMG.
- If you encounter missing library errors, ensure you have installed all dependencies as above.

---

## Credits

- **libltc** — SMPTE timecode decoding powered by [libltc](https://github.com/x42/libltc) (huge thanks to the libltc team!)
- UI and packaging: [Your Name or Team]
- Special thanks to all testers and contributors

---

## License

All rights reserved.  
This software is not open source. Please do not redistribute or modify without permission.

---

