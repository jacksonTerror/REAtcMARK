import numpy as np
import subprocess, shutil, os, sys
import csv
import logging
from typing import Dict, Optional, Callable, Tuple

try:
    from ltc_wrapper import LTCWrapper  # type: ignore
except ImportError:
    print("Warning: ltc_wrapper not found. Make sure to build it first.")
    LTCWrapper = None

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class SMPTEDetector:
    def __init__(self, fps: int = 30):
        """Initialize SMPTE detector.

        The actual LTC decoder instance will be created *per file* using that
        file's native sample-rate so that we never feed mismatched data to the
        underlying libltc decoder (mismatched rates are the primary cause of
        the previously observed «no markers found» issue).
        """
        if LTCWrapper is None:
            raise RuntimeError("LTC wrapper not available. Please build it first.")

        self.fps = fps
        # The decoder is created later inside process_file once we know the
        # file's real sample-rate.
        self.ltc_decoder = None
        
    def format_time(self, seconds: float, fps: int = 30) -> str:
        """Format time in seconds to HH:MM:SS:FF format"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        frames = int((seconds % 1) * fps)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}:{frames:02d}"
        
    def _load_mappings(self, mapping_path: str) -> Dict[str, str]:
        """Load SMPTE to marker name mappings from a CSV file using the csv module."""
        mappings = {}
        try:
            with open(mapping_path, mode='r', encoding='utf-8', newline='') as infile:
                reader = csv.DictReader(infile)
                if reader.fieldnames:
                    reader.fieldnames = [name.strip() for name in reader.fieldnames]

                for row in reader:
                    # Handle potential variations in column names ('SMPTE Code' vs 'smpte_code')
                    smpte = row.get('SMPTE Code') or row.get('smpte_code')
                    name = row.get('Marker Name') or row.get('marker_name')
                    if smpte and name:
                        mappings[smpte.strip()] = name.strip()
            logger.info(f"Loaded {len(mappings)} mappings from {mapping_path}")
        except Exception as e:
            logger.error(f"Failed to load mappings from {mapping_path}: {e}", exc_info=True)
            # Return empty dict if loading fails
            return {}
        return mappings
        
    # ------------------------------------------------------------------
    # Internal helpers – FFmpeg streaming interface
    # ------------------------------------------------------------------

    def _check_ffmpeg(self) -> str:
        """Return the ffmpeg executable to use or raise if not found."""
        exe = shutil.which("ffmpeg")
        if exe is None:
            raise RuntimeError("FFmpeg is required but was not found in your PATH.")
        return exe

    def _pcm_chunks(self, path: str, rate: int, dur: float):
        """Yield raw unsigned-8-bit PCM blocks of `dur` seconds from *path*."""
        ffmpeg = self._check_ffmpeg()
        cmd = [ffmpeg, "-nostdin", "-i", path,
               "-ar", str(rate), "-ac", "1",
               # Use 32-bit little-endian floats instead of 8-bit unsigned PCM. This avoids the heavy
               # quantisation noise of 8-bit audio, giving the LTC decoder a much cleaner signal.
               # libltc works perfectly with normalised float samples in the range −1…1, which is
               # exactly what ffmpeg outputs in f32le.
               "-f", "f32le",
               "-loglevel", "error", "-"]

        # Hide any transient console window on Windows by using CREATE_NO_WINDOW.
        creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0  # type: ignore[attr-defined]

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            bufsize=rate,
            creationflags=creationflags,
        )
        assert proc.stdout is not None  # for mypy/pylint
        # Each sample is now 4-bytes (32-bit float)
        size = int(rate * dur * 4)
        while True:
            buf = proc.stdout.read(size)
            if len(buf) < size:
                break
            yield buf
        proc.stdout.close(); proc.wait()
        
    def process_file(self, audio_path: str, mapping_path: str, 
                    callback: Optional[Callable[[str], None]] = None) -> Dict[str, float]:
        """
        Process an audio file to detect SMPTE timecodes and map them to markers
        
        Args:
            audio_path: Path to the audio file to process
            mapping_path: Path to the CSV file containing SMPTE to marker mappings
            callback: Optional callback function to report progress
            
        Returns:
            Dictionary mapping marker names to their positions in seconds
        """
        # Load the mapping file
        mappings = self._load_mappings(mapping_path)
        if callback is not None:
            callback(f"Loaded {len(mappings)} SMPTE mappings")  # type: ignore
            
        # ------------------------------------------------------------------
        # Pre-compute mapping codes → absolute frame numbers for fuzzy match
        # ------------------------------------------------------------------

        def _code_to_abs(code: str) -> int:
            hh, mm, ss, ff = map(int, code.split(":"))
            return (((hh * 60) + mm) * 60 + ss) * self.fps + ff

        tolerance = 3  # frames; user said ±3-5 is acceptable

        mapping_table: list[tuple[int, str]] = []  # (absolute_frames, name)
        for tc, name in mappings.items():
            try:
                mapping_table.append((_code_to_abs(tc), name))
            except ValueError:
                logger.warning("Invalid SMPTE code in mapping CSV: %s", tc)

        mapping_table.sort(key=lambda t: t[0])  # optional, for predictable order

        # We now ALLOW the same marker to be emitted multiple times (e.g. the
        # same song appears twice in one show).  To avoid a flood of duplicate
        # markers coming from consecutive LTC frames of the same burst we keep
        # the time we last emitted each *marker name* and suppress any repeat
        # that occurs within <min_gap_sec.

        last_emitted: dict[str, float] = {}
        min_gap_sec = 1.0  # don’t re-emit the very same marker within 1 second

        # ------------------------------------------------------------------
        # Stream audio via FFmpeg → unsigned-8-bit mono @ 48 kHz (libltc-friendly)
        # ------------------------------------------------------------------

        target_rate  = 48000

        # A shorter chunk helps when the LTC burst is brief (e.g. 1-2 frames). 50 ms is a
        # good compromise between decoder throughput and not missing boundaries.
        chunk_dur_s  = 0.05  # 50 ms
        decoder      = LTCWrapper(target_rate, self.fps)
        self.ltc_decoder = decoder

        if callback is not None:
            callback("Scanning audio file…")  # type: ignore

        detected_codes: Dict[str, float] = {}
        idx = 0
        for raw in self._pcm_chunks(audio_path, target_rate, chunk_dur_s):

            # The stream is already 32-bit float in the range −1…1, so we can convert directly
            # without any re-scaling or quantisation loss.
            samples = np.frombuffer(raw, np.float32)

            # Auto-gain: if the LTC stripe is very quiet in the mix we normalise this
            # chunk so its peak hits 0 dBFS before we convert to unsigned-char bytes.
            peak = np.abs(samples).max(initial=0.0)
            if 0.0 < peak < 0.2:  # only boost when it’s **really** quiet (<-14 dBFS)
                samples = samples / peak
            # 1) Process the fresh audio chunk
            result = decoder.decode_audio(samples)  # type: ignore

            def _handle(res):
                frame, secs, mins, hours, off = res
                timecode = f"{hours:02d}:{mins:02d}:{secs:02d}:{frame:02d}"
                pos_sec  = idx * chunk_dur_s + off

                abs_frames = _code_to_abs(timecode)

                # Fuzzy-match: pick the *nearest* target whose code is within ±tolerance
                match_name: Optional[str] = None
                nearest_delta = tolerance + 1  # start outside range
                for tgt_frames, tgt_name in mapping_table:
                    delta = abs(abs_frames - tgt_frames)
                    if delta <= tolerance and delta < nearest_delta:
                        nearest_delta = delta
                        match_name = tgt_name

                if match_name is not None:
                    pos_sec = idx * chunk_dur_s + off

                    # Time-gap suppression
                    last_t = last_emitted.get(match_name, -9999.0)
                    if pos_sec - last_t >= min_gap_sec:
                        detected_codes.setdefault(match_name, pos_sec)
                        last_emitted[match_name] = pos_sec
                        if callback is not None:
                            callback(
                                f"Found {timecode} → {match_name} at {self.format_time(pos_sec, self.fps)}"  # type: ignore
                            )
                else:
                    if callback is not None:
                        callback(
                            f"Found unmapped {timecode} at {self.format_time(pos_sec, self.fps)}"  # type: ignore
                        )

            if result:
                _handle(result)

                # 2) Flush any additional queued frames by calling the decoder
                #    with a zero-length buffer until nothing is returned.
                empty = np.empty((0,), dtype=np.float32)
                while True:
                    extra = decoder.decode_audio(empty)  # type: ignore
                    if not extra:
                        break
                    _handle(extra)

            idx += 1
        return detected_codes 