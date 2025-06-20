from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class ShowMetadata:
    """Represents metadata for a show recording"""
    date: datetime
    band_name: str
    city: str
    venue: Optional[str] = None
    
    def format_filename(self, suffix: str = "") -> str:
        """Generate a filename based on metadata"""
        date_str = self.date.strftime("%Y.%m.%d")
        # Clean up band name and city for filename use
        band = "".join(c for c in self.band_name if c.isalnum() or c in " -_")
        city = "".join(c for c in self.city if c.isalnum() or c in " -_")
        
        parts = [date_str, band, city]
        if suffix:
            parts.append(suffix)
            
        return "_".join(parts)
    
    def format_header(self) -> str:
        """Generate a header for text files"""
        date_str = self.date.strftime("%B %d, %Y")
        parts = [
            f"Date: {date_str}",
            f"Band: {self.band_name}",
            f"City: {self.city}"
        ]
        if self.venue:
            parts.append(f"Venue: {self.venue}")
        
        return "\n".join(parts)
    
    @classmethod
    def create_from_user_input(cls, date_str: str, band: str, city: str, venue: Optional[str] = None) -> 'ShowMetadata':
        """Create metadata from user input strings"""
        try:
            # Try different date formats
            for fmt in ["%Y-%m-%d", "%Y.%m.%d", "%Y/%m/%d", "%d-%m-%Y", "%d.%m.%Y", "%d/%m/%Y"]:
                try:
                    date = datetime.strptime(date_str, fmt)
                    return cls(
                        date=date,
                        band_name=band.strip(),
                        city=city.strip(),
                        venue=venue.strip() if venue else None
                    )
                except ValueError:
                    continue
            raise ValueError("Could not parse date")
        except Exception as e:
            raise ValueError(f"Invalid metadata format: {str(e)}")

# Example usage:
# metadata = ShowMetadata.create_from_user_input(
#     date_str="2024-03-21",
#     band="Cosmic Selector",
#     city="Austin",
#     venue="Huron"
# )
# 
# filename = metadata.format_filename("setlist.txt")
# # Result: "2024.03.21_CosmicSelector_Austin_setlist.txt" 