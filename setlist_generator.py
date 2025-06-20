from typing import List, Optional
from dataclasses import dataclass
from datetime import datetime
import csv
from pathlib import Path
from show_metadata import ShowMetadata
from smpte_detector import TimecodeMatch

@dataclass
class SetListEntry:
    """Represents a single entry in the set list"""
    number: int
    name: str
    real_time: str  # HH:MM:SS:FF
    smpte_trigger: str  # HH:MM:SS:FF

class SetListGenerator:
    def __init__(self, metadata: ShowMetadata):
        self.metadata = metadata
        self.entries: List[SetListEntry] = []
        
    def add_match(self, match: TimecodeMatch, formatted_time: str):
        """Add a matched timecode to the set list"""
        if match.marker_number is None or match.marker_name is None:
            return
            
        entry = SetListEntry(
            number=match.marker_number,
            name=match.marker_name,
            real_time=formatted_time,
            smpte_trigger=match.smpte_time
        )
        self.entries.append(entry)
        
    def generate_reaper_csv(self, output_path: str):
        """Generate Reaper markers CSV file"""
        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['#', 'Name', 'Start', 'End', 'Length'])
            
            for entry in sorted(self.entries, key=lambda x: x.number):
                marker_name = f"{entry.number:02d}-{entry.name}"
                writer.writerow([
                    f"M{entry.number}",
                    marker_name,
                    entry.real_time,
                    "",  # End time (empty for markers)
                    ""   # Length (empty for markers)
                ])
                
    def generate_setlist_txt(self, output_path: str, include_smpte: bool = False):
        """Generate human-readable set list text file"""
        with open(output_path, 'w') as f:
            # Write header
            f.write(self.metadata.format_header())
            f.write("\n\nSet List:\n")
            
            # Write entries
            for entry in sorted(self.entries, key=lambda x: x.number):
                f.write(f"\n{entry.number}. {entry.name}")
                f.write(f" (at {entry.real_time})")
                
            # Optionally add SMPTE reference points
            if include_smpte:
                f.write("\n\nSMPTE Reference Points:\n")
                for entry in sorted(self.entries, key=lambda x: x.number):
                    f.write(f"\n{entry.number}. {entry.smpte_trigger} -> {entry.real_time}")
                    
    def generate_all_outputs(self, base_path: str):
        """Generate all output files"""
        # Create base filename from metadata
        base_filename = self.metadata.format_filename()
        path = Path(base_path)
        
        # Generate Reaper markers
        reaper_path = str(path / f"{base_filename}_markers.csv")
        self.generate_reaper_csv(reaper_path)
        
        # Generate basic set list
        setlist_path = str(path / f"{base_filename}_setlist.txt")
        self.generate_setlist_txt(setlist_path)
        
        # Generate detailed set list with SMPTE
        detailed_path = str(path / f"{base_filename}_setlist_detailed.txt")
        self.generate_setlist_txt(detailed_path, include_smpte=True)
        
    def get_preview(self) -> str:
        """Generate a preview of the set list for the UI"""
        lines = ["Detected Set List:"]
        
        for entry in sorted(self.entries, key=lambda x: x.number):
            lines.append(f"\n{entry.number}. {entry.name}")
            lines.append(f"   Time: {entry.real_time}")
            lines.append(f"   SMPTE: {entry.smpte_trigger}")
            
        return "\n".join(lines) 