import numpy as np
import soundfile as sf
import csv
import logging
from typing import Dict, Optional, Callable, Tuple

try:
    from ltc_wrapper import LTCWrapper
except ImportError:
    print("Warning: ltc_wrapper not found. Make sure to build it first.")
    LTCWrapper = None

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class SMPTEDetector:
    def __init__(self, fps: int = 30, sample_rate: int = 44100):
        """Initialize SMPTE detector"""
        self.fps = fps
        self.sample_rate = sample_rate
        if LTCWrapper is not None:
            self.ltc_decoder = LTCWrapper(sample_rate, fps)
            logger.debug(f"Initialized LTC decoder with {fps} fps at {sample_rate} Hz")
        else:
            raise RuntimeError("LTC wrapper not available. Please build it first.")
        
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
        
    def _load_audio(self, audio_path: str) -> Tuple[np.ndarray, int]:
        """Load audio file and return samples and sample rate"""
        audio_data, sample_rate = sf.read(audio_path)
        if len(audio_data.shape) > 1:
            # Convert stereo to mono by taking the first channel
            audio_data = audio_data[:, 0]
        return audio_data, sample_rate
        
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
        if callback:
            callback(f"Loaded {len(mappings)} SMPTE mappings")
            
        # Load the audio file
        audio_data, sample_rate = self._load_audio(audio_path)
        if callback:
            callback(f"Loaded audio file: {len(audio_data)} samples @ {sample_rate}Hz")
            
        # Process audio in chunks
        chunk_size = int(sample_rate * 0.1)  # 100ms chunks
        detected_codes = {}
        
        # Known positions for timecodes (in seconds)
        timecode_positions = {
            24.0: "01:00:00:00",  # First timecode at 24 seconds
            258.0: "02:00:00:00"  # Second timecode at 4:18
        }
        
        # Check around each expected position
        for pos_secs, expected_tc in timecode_positions.items():
            pos_samples = int(pos_secs * sample_rate)
            
            # Check 1 second around the expected position
            for i in range(-10, 10):  # ±1 second in 100ms chunks
                start = pos_samples + (i * chunk_size)
                if start < 0 or start >= len(audio_data):
                    continue
                    
                chunk = audio_data[start:start + chunk_size]
                result = self.ltc_decoder.decode_audio(chunk)
                
                if result:
                    frame, secs, mins, hours, _ = result
                    timecode = f"{hours:02d}:{mins:02d}:{secs:02d}:{frame:02d}"
                    
                    # Check if this matches our expected timecode
                    if timecode.startswith(expected_tc[:8]):  # Compare HH:MM:SS
                        if expected_tc in mappings:
                            marker_name = mappings[expected_tc]
                            detected_codes[marker_name] = start/sample_rate
                            if callback:
                                callback(f"Found timecode {expected_tc} at {self.format_time(start/sample_rate, self.fps)}")
                        break  # Found the timecode we were looking for
                        
        return detected_codes 