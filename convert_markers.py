import csv
import sys

def parse_reaper_time(time_str):
    """Parse Reaper's time format (e.g. '617.1.00') to seconds"""
    if not time_str:
        return 0
    
    parts = time_str.split('.')
    seconds = float(parts[0])
    if len(parts) > 1:
        # Handle subseconds if present
        subseconds = float('0.' + parts[1])
        seconds += subseconds
    
    return seconds

def seconds_to_smpte(seconds, fps=30):
    """Convert seconds to SMPTE timecode"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    frames = int((seconds % 1) * fps)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}:{frames:02d}"

def convert_csv(input_file, output_file):
    """Convert Reaper's exported CSV format to import format"""
    with open(input_file, 'r') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    # Convert to import format
    output_rows = []
    for row in rows:
        # Convert time from Reaper format to SMPTE
        start_time = parse_reaper_time(row['Start'])
        smpte_time = seconds_to_smpte(start_time)
        
        output_rows.append({
            'Number': row['#'].replace('M', ''),  # Remove 'M' prefix
            'Name': row['Name'],
            'Start': smpte_time,
            'End': smpte_time,  # Point markers have same start/end
            'Length': '0',
            'Color': ''
        })
    
    # Write output file
    with open(output_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['Number', 'Name', 'Start', 'End', 'Length', 'Color'])
        writer.writeheader()
        writer.writerows(output_rows)

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python convert_markers.py input.csv output.csv")
        sys.exit(1)
    
    convert_csv(sys.argv[1], sys.argv[2])
    print("Conversion complete!") 