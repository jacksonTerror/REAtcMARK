import logging
from pathlib import Path
from smpte_detector import SMPTEDetector

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_smpte_detection():
    # Initialize detector with 30fps
    detector = SMPTEDetector(fps=30)
    
    # Test files
    test_file = "TestAudio/2025.06.18_SMPTE-test.wav"
    mapping_file = "TestAudio/2025.06.18_HURON_Worcester.csv"
    
    # Load audio directly
    audio_data, sample_rate = detector._load_audio(test_file)
    logger.info(f"Loaded audio file: {Path(test_file).name}")
    logger.info(f"Sample rate: {sample_rate} Hz")
    logger.info(f"Total duration: {len(audio_data)/sample_rate:.2f} seconds")
    
    # Check specific positions where we expect timecodes
    # First timecode at 00:00:24:00 (24 seconds)
    pos1_samples = int(24 * sample_rate)
    chunk_size = int(sample_rate * 0.1)  # 100ms chunks
    
    logger.info("\nChecking first position (24 seconds)...")
    for i in range(-5, 5):  # Check 1 second around the expected position
        start = pos1_samples + (i * chunk_size)
        chunk = audio_data[start:start + chunk_size]
        timecode = detector.ltc_decoder.decode_audio(chunk)
        if timecode:
            frame, secs, mins, hours, position = timecode
            tc_str = f"{hours:02d}:{mins:02d}:{secs:02d}:{frame:02d}"
            logger.info(f"Found timecode {tc_str} at {start/sample_rate:.3f} seconds")
    
    # Second timecode at 00:04:18:00 (258 seconds)
    pos2_samples = int(258 * sample_rate)
    
    logger.info("\nChecking second position (258 seconds)...")
    for i in range(-5, 5):  # Check 1 second around the expected position
        start = pos2_samples + (i * chunk_size)
        chunk = audio_data[start:start + chunk_size]
        timecode = detector.ltc_decoder.decode_audio(chunk)
        if timecode:
            frame, secs, mins, hours, position = timecode
            tc_str = f"{hours:02d}:{mins:02d}:{secs:02d}:{frame:02d}"
            logger.info(f"Found timecode {tc_str} at {start/sample_rate:.3f} seconds")

if __name__ == "__main__":
    test_smpte_detection() 