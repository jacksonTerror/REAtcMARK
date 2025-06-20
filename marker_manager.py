from dataclasses import dataclass
from typing import List, Dict
import csv
from pathlib import Path

@dataclass
class Marker:
    timecode: str
    name: str
    time_seconds: float = 0.0

class MarkerManager:
    def __init__(self):
        self.markers: List[Marker] = []
        self.timecode_map: Dict[str, str] = {}
        
    def load_timecode_map(self, csv_path: str):
        """Load SMPTE timecode to marker name mappings from a CSV file."""
        try:
            with open(csv_path, mode='r', encoding='utf-8', newline='') as infile:
                reader = csv.DictReader(infile)
                if reader.fieldnames:
                    reader.fieldnames = [name.strip() for name in reader.fieldnames]

                for row in reader:
                    # Handle potential variations in column names for backward compatibility
                    smpte = row.get('SMPTE Code') or row.get('smpte_code')
                    name = row.get('Marker Name') or row.get('marker_name')
                    if smpte and name:
                        self.timecode_map[smpte.strip()] = name.strip()
        except Exception as e:
            # Handle exceptions, e.g., file not found or malformed
            print(f"Error loading timecode map: {e}")
            self.timecode_map = {}
    
    def add_marker(self, timecode: str, time_seconds: float, name: str | None = None):
        """Add a new marker based on detected timecode"""
        if name is None:
            name = self.timecode_map.get(timecode, f"Unknown_{timecode}")
        marker = Marker(timecode=timecode, name=name, time_seconds=time_seconds)
        self.markers.append(marker)
        
    def smpte_to_seconds(self, timecode: str) -> float:
        """Convert SMPTE timecode (HH:MM:SS:FF) to seconds"""
        hours, minutes, seconds, frames = map(int, timecode.split(':'))
        total_seconds = hours * 3600 + minutes * 60 + seconds + frames / 30.0  # Assuming 30fps
        return total_seconds

    def export_reaper_csv(self, output_path: str):
        """Export markers in exact Reaper format"""
        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)
            # Write Reaper's header
            writer.writerow(['#', 'Name', 'Start', 'End', 'Length'])
            
            # Sort markers by their actual project time position
            for idx, marker in enumerate(sorted(self.markers, key=lambda x: x.time_seconds), 1):
                # Convert seconds to HH:MM:SS:FF format (assuming 30fps)
                total_seconds = int(marker.time_seconds)
                frames = int((marker.time_seconds - total_seconds) * 30)
                
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                seconds = total_seconds % 60
                
                time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}:{frames:02d}"
                marker_num = f"M{idx}"
                
                # Write row with empty End and Length fields
                writer.writerow([marker_num, marker.name, time_str, '', ''])
                
    def export_logic_csv(self, output_path: str):
        """Export markers in Logic Pro CSV format"""
        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Name', 'Time'])
            for marker in sorted(self.markers, key=lambda x: x.time_seconds):
                time_str = f"{int(marker.time_seconds // 3600):02d}:{int((marker.time_seconds % 3600) // 60):02d}:{int(marker.time_seconds % 60):02d}"
                writer.writerow([marker.name, time_str])
                
    def export_protools_txt(self, output_path: str):
        """Export markers in Pro Tools text format"""
        with open(output_path, 'w') as f:
            f.write("Session Name: SMPTE Markers\n")
            f.write("Sample Rate: 48000\n")
            f.write("Bit Depth: 24\n")
            f.write("Time Code Format: 30 Frame\n")
            f.write("\nMarkers:\n")
            for marker in sorted(self.markers, key=lambda x: x.time_seconds):
                f.write(f"{marker.timecode}\t{marker.name}\n") 