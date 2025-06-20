from marker_manager import MarkerManager

def test_export():
    # Create a marker manager
    mm = MarkerManager()
    
    # Add test markers at the specified real-world times with exact names from Reaper export
    # 01:00:00:00 SMPTE appears at 00:00:24:00
    mm.add_marker("01:00:00:00", 24.0, "Start of show")  # 24 seconds
    
    # 02:00:00:00 SMPTE appears at 00:04:18:00
    mm.add_marker("02:00:00:00", 4 * 60 + 18, "Middle of show")  # 4 minutes and 18 seconds
    
    # Export in Reaper format
    mm.export_reaper_csv("test_export_markers.csv")
    
    print("Test export completed. Please check test_export_markers.csv")

if __name__ == "__main__":
    test_export() 