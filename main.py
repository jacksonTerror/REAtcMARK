import sys
from pathlib import Path
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                         QHBoxLayout, QPushButton, QLabel, QFileDialog,
                         QLineEdit, QMessageBox, QGroupBox, QFormLayout,
                         QDateEdit, QComboBox, QTextEdit, QTableWidgetItem,
                         QCheckBox, QFrame)
from PyQt6.QtCore import Qt, QDate, QTimer
from PyQt6.QtGui import QPixmap, QFont, QPalette, QColor, QIcon
import json
from smpte_detector import SMPTEDetector
from mapping_editor import SMPTEMappingEditor
from marker_manager import MarkerManager
import os
import platform
from datetime import datetime
import logging
from typing import Optional

# Set up logging
logger = logging.getLogger(__name__)

def get_config_path() -> Path:
    """Get the platform-specific path for the config file."""
    app_name = "REAtcMARK"
    
    # macOS: ~/Library/Application Support/<AppName>
    if sys.platform == "darwin":
        config_dir = Path.home() / "Library" / "Application Support" / app_name
    # Windows: %APPDATA%\<AppName>
    elif sys.platform == "win32":
        config_dir = Path(os.getenv('APPDATA', '')) / app_name
    # Linux: ~/.config/<AppName>
    else:
        config_dir = Path.home() / ".config" / app_name
        
    # Create the directory if it doesn't exist
    config_dir.mkdir(parents=True, exist_ok=True)
    
    return config_dir / "config.json"

CONFIG_FILE = get_config_path()

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for cx_Freeze """
    # For development
    base_path = os.path.abspath(".")

    # If frozen (packaged by cx_Freeze, etc.)
    if getattr(sys, 'frozen', False):
        # On macOS, resources are in a 'Resources' directory
        if sys.platform == "darwin":
            base_path = os.path.join(os.path.dirname(sys.executable), "..", "Resources")
        else:
            # On other OS, they are in the same directory as the executable
            base_path = os.path.dirname(sys.executable)

    return os.path.join(base_path, relative_path)

class LCDDisplay(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QFrame {
                background: #1a1a1a;
                border: 2px solid #404040;
                border-radius: 4px;
                padding: 4px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(2)
        layout.setContentsMargins(8, 4, 8, 4)
        
        # Labels row
        labels = QHBoxLayout()
        for text in ["HRS", "MIN", "SEC", "FRAMES"]:
            label = QLabel(text)
            label.setStyleSheet("color: #808080; font-size: 10px;")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            labels.addWidget(label)
        layout.addLayout(labels)
        
        # LCD time display
        self.time_display = QLabel("00:00:00:00")
        self.time_display.setStyleSheet("""
            QLabel {
                color: #4fc3f7;
                background: #000000;
                border: 1px solid #404040;
                border-radius: 2px;
                padding: 4px;
                font-family: "Courier New", monospace;
                font-size: 24px;
            }
        """)
        self.time_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.time_display)
        
        # Status indicator
        status_layout = QHBoxLayout()
        status_layout.addStretch()
        self.status = QLabel("ON")
        self.status.setStyleSheet("""
            QLabel {
                color: #4fc3f7;
                font-size: 10px;
                padding-right: 4px;
            }
        """)
        status_layout.addWidget(self.status)
        layout.addLayout(status_layout)
        
        # Update timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)  # Update every second
        
    def update_time(self):
        now = datetime.now()
        frames = int((now.microsecond / 1000000) * 30)  # Assuming 30fps
        self.time_display.setText(f"{now.hour:02d}:{now.minute:02d}:{now.second:02d}:{frames:02d}")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("REAtcMARK")
        self.setMinimumWidth(740)  # Increased to fit new logo
        
        # Set dark theme colors
        dark_palette = """
            QMainWindow, QWidget {
                background: #2b2b2b;
                color: #e0e0e0;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #404040;
                border-radius: 6px;
                margin-top: 1ex;
                color: #e0e0e0;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px;
            }
            QLineEdit, QDateEdit, QComboBox {
                background: #363636;
                color: #e0e0e0;
                border: 1px solid #404040;
                border-radius: 4px;
                padding: 5px;
                min-height: 20px;
            }
            QLineEdit:focus, QDateEdit:focus, QComboBox:focus {
                border: 1px solid #5294e2;
            }
            QLineEdit:disabled {
                background: #2b2b2b;
                color: #808080;
            }
            QPushButton {
                background: #363636;
                color: #e0e0e0;
                border: 1px solid #404040;
                border-radius: 4px;
                padding: 5px 15px;
                min-height: 20px;
            }
            QPushButton:hover {
                background: #404040;
            }
            QPushButton:pressed {
                background: #2b2b2b;
            }
            QTextEdit {
                background: #363636;
                color: #e0e0e0;
                border: 1px solid #404040;
                border-radius: 4px;
                padding: 5px;
                font-family: monospace;
            }
            QLabel {
                color: #e0e0e0;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                width: 8px;
                height: 8px;
                border: 2px solid #e0e0e0;
                border-top: none;
                border-right: none;
                transform: rotate(-45deg);
                margin-top: -3px;
            }
        """
        self.setStyleSheet(dark_palette)
        
        # Initialize config and instance variables
        self.config = self.load_config()
        self.current_mapping_file_full_path: Optional[str] = None
        self.current_audio_file_full_path: Optional[str] = None
        self.current_export_folder_full_path: Optional[str] = None
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(24, 24, 24, 24)
        
        # Header with Logo
        header_layout = QHBoxLayout()
        logo_label = QLabel()
        logo_path = resource_path("ReatcMarkLOGOheader.png")
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            logo_label.setPixmap(pixmap)
        else:
            logo_label.setText("REAtcMARK") # Fallback text
        
        # Center the logo using stretchable spacers
        header_layout.addStretch(1)
        header_layout.addWidget(logo_label)
        header_layout.addStretch(1)
        
        main_layout.addLayout(header_layout)

        # Metadata Group
        metadata_group = QGroupBox("Show Metadata")
        metadata_layout = QFormLayout()
        metadata_layout.setSpacing(12)
        metadata_layout.setContentsMargins(15, 15, 15, 15)
        metadata_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #FFD600;
                border-radius: 6px;
                margin-top: 1ex;
                color: #e0e0e0;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px;
            }
        """)
        
        # Set fixed label width and alignment
        metadata_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        metadata_layout.setHorizontalSpacing(20)  # Space between label and field
        
        # Create a widget to enforce minimum label column width
        label_size_widget = QLabel()
        label_size_widget.setFixedWidth(100)  # Fixed width for label column
        metadata_layout.addRow(label_size_widget, QWidget())  # Hidden row to enforce width
        label_size_widget.hide()  # Hide the dummy row
        
        # Date field (keep current width)
        self.date_edit = QDateEdit()
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.dateChanged.connect(self.update_filename_preview)
        self.date_edit.setFixedWidth(150)
        date_label = QLabel("Date:")
        date_label.setMinimumWidth(100)  # Consistent with label column width
        metadata_layout.addRow(date_label, self.date_edit)
        
        # Artist field (required)
        self.band_edit = QLineEdit()
        self.band_edit.setPlaceholderText("Enter artist name")
        self.band_edit.textChanged.connect(self.update_filename_preview)
        self.band_edit.setFixedWidth(350)  # Slightly wider for better text display
        artist_label = QLabel("* Artist:")
        artist_label.setMinimumWidth(100)  # Consistent with label column width
        metadata_layout.addRow(artist_label, self.band_edit)
        
        # City field (required)
        self.city_edit = QLineEdit()
        self.city_edit.setPlaceholderText("Enter city name")
        self.city_edit.textChanged.connect(self.update_filename_preview)
        self.city_edit.setFixedWidth(350)  # Consistent with artist field
        city_label = QLabel("* City:")
        city_label.setMinimumWidth(100)  # Consistent with label column width
        metadata_layout.addRow(city_label, self.city_edit)
        
        # Export folder selection
        export_folder_layout = QVBoxLayout()
        export_folder_layout.setSpacing(8)
        export_folder_layout.setContentsMargins(0, 0, 0, 0)  # Remove any extra margins
        
        # Create a container widget to hold the export folder contents
        export_folder_container = QWidget()
        export_folder_container.setFixedWidth(350)  # Match other fields width
        
        self.export_folder_label = QLabel("Default (same as application)")
        self.export_folder_label.setFixedWidth(350)  # Consistent with other fields
        self.export_folder_label.setStyleSheet("""
            QLabel {
                color: #a0a0a0;
                padding: 8px;
                background: #363636;
                border-radius: 4px;
                min-height: 20px;
            }
        """)
        export_folder_layout.addWidget(self.export_folder_label)
        
        # Buttons row
        folder_buttons = QHBoxLayout()
        folder_buttons.setSpacing(8)
        folder_buttons.setContentsMargins(0, 0, 0, 0)  # Remove any extra margins
        
        select_folder_btn = QPushButton("Select Folder")
        select_folder_btn.setMinimumWidth(100)
        select_folder_btn.clicked.connect(self.select_export_folder)
        folder_buttons.addWidget(select_folder_btn)
        
        self.remember_folder_checkbox = QCheckBox("Remember this")
        folder_buttons.addWidget(self.remember_folder_checkbox)
        folder_buttons.addStretch()
        
        export_folder_layout.addLayout(folder_buttons)
        
        export_folder_container.setLayout(export_folder_layout)
        
        # Add to form layout with proper label
        export_folder_label = QLabel("Export Folder:")
        export_folder_label.setMinimumWidth(100)  # Consistent with label column width
        metadata_layout.addRow(export_folder_label, export_folder_container)
        
        # Output Files preview
        self.filename_preview = QLabel()
        self.filename_preview.setFixedWidth(350)  # Consistent with other fields
        self.filename_preview.setStyleSheet("""
            QLabel {
                color: #a0a0a0;
                padding: 8px;
                background: #363636;
                border-radius: 4px;
                margin-top: 8px;
            }
        """)
        output_files_label = QLabel("Output Files:")
        output_files_label.setMinimumWidth(100)  # Consistent with label column width
        metadata_layout.addRow(output_files_label, self.filename_preview)
        
        # Load/Save defaults
        defaults_layout = QHBoxLayout()
        defaults_layout.setSpacing(8)
        defaults_layout.setContentsMargins(0, 8, 0, 0)  # Add top margin only
        
        # Create a container widget to hold the buttons
        defaults_container = QWidget()
        defaults_container.setFixedWidth(350)  # Match field width
        
        load_defaults_btn = QPushButton("Load Defaults")
        load_defaults_btn.clicked.connect(self.load_defaults)
        defaults_layout.addWidget(load_defaults_btn)
        
        save_defaults_btn = QPushButton("Save as Defaults")
        save_defaults_btn.clicked.connect(self.save_defaults)
        defaults_layout.addWidget(save_defaults_btn)
        defaults_layout.addStretch()
        
        defaults_container.setLayout(defaults_layout)
        
        # Empty label to maintain column width
        empty_label = QLabel("")
        empty_label.setMinimumWidth(100)  # Consistent with label column width
        metadata_layout.addRow(empty_label, defaults_container)
        
        # --- Style top section buttons (yellow/gold) ---
        yellow_btn_style = """
            QPushButton {
                background: #FFD600;
                color: #222;
                border: none;
                border-radius: 4px;
                padding: 6px 18px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #FFEA00;
            }
            QPushButton:pressed {
                background: #FFC400;
            }
        """
        # Apply to Select Folder, Load Defaults, Save as Defaults
        select_folder_btn.setStyleSheet(yellow_btn_style)
        load_defaults_btn.setStyleSheet(yellow_btn_style)
        save_defaults_btn.setStyleSheet(yellow_btn_style)

        metadata_group.setLayout(metadata_layout)
        main_layout.addWidget(metadata_group)
        
        # SMPTE Processing Group
        smpte_group = QGroupBox("SMPTE Processing")
        smpte_layout = QVBoxLayout()
        smpte_layout.setSpacing(12)
        smpte_layout.setContentsMargins(15, 15, 15, 15)
        smpte_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #FF9800;
                border-radius: 6px;
                margin-top: 1ex;
                color: #e0e0e0;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px;
            }
        """)
        
        # Audio File
        audio_layout = QHBoxLayout()
        self.file_path_label = QLabel("No file selected")
        self.file_path_label.setWordWrap(True)
        self.file_path_label.setStyleSheet("""
            QLabel {
                color: #a0a0a0;
                padding: 8px;
                background: #363636;
                border-radius: 4px;
                min-height: 20px;
            }
        """)
        audio_layout.addWidget(self.file_path_label, stretch=1)
        
        self.select_file_btn = QPushButton("Select File")
        self.select_file_btn.setMinimumWidth(100)
        self.select_file_btn.clicked.connect(self.select_audio_file)
        audio_layout.addWidget(self.select_file_btn)
        
        audio_container = QWidget()
        audio_container.setLayout(audio_layout)
        smpte_layout.addWidget(audio_container)
        
        # SMPTE Mapping
        mapping_layout = QVBoxLayout()
        
        # Path display
        self.mapping_path_label = QLabel("No mapping file selected")
        self.mapping_path_label.setWordWrap(True)
        self.mapping_path_label.setStyleSheet("""
            QLabel {
                color: #a0a0a0;
                padding: 8px;
                background: #363636;
                border-radius: 4px;
                min-height: 20px;
            }
        """)
        mapping_layout.addWidget(self.mapping_path_label)
        
        # Button row
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)
        
        select_mapping_btn = QPushButton("Select File")
        select_mapping_btn.setMinimumWidth(100)
        select_mapping_btn.clicked.connect(self.select_mapping_file)
        button_layout.addWidget(select_mapping_btn)
        
        edit_mapping_btn = QPushButton("Edit")
        edit_mapping_btn.setMinimumWidth(80)
        edit_mapping_btn.clicked.connect(lambda: self.open_mapping_editor(is_new_file=False))
        button_layout.addWidget(edit_mapping_btn)
        
        create_mapping_btn = QPushButton("Create New")
        create_mapping_btn.setMinimumWidth(100)
        create_mapping_btn.clicked.connect(lambda: self.open_mapping_editor(is_new_file=True))
        button_layout.addWidget(create_mapping_btn)
        
        clear_mapping_btn = QPushButton("Clear")
        clear_mapping_btn.setMinimumWidth(80)
        clear_mapping_btn.clicked.connect(self.clear_mapping_file)
        button_layout.addWidget(clear_mapping_btn)
        
        button_layout.addStretch()
        
        self.remember_mapping_checkbox = QCheckBox("Remember this")
        self.remember_mapping_checkbox.setChecked(True)
        button_layout.addWidget(self.remember_mapping_checkbox)
        
        mapping_layout.addLayout(button_layout)
        
        mapping_container = QWidget()
        mapping_container.setLayout(mapping_layout)
        smpte_layout.addWidget(mapping_container)

        # Controls row (Process File, Frame Rate, Open Output Folder)
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(12)

        # Add controls directly to the layout for correct alignment
        self.start_btn = QPushButton("Process File")
        self.start_btn.setMinimumWidth(130)  # Increased minimum width
        self.start_btn.clicked.connect(self.process_file)
        controls_layout.addWidget(self.start_btn)

        fps_label = QLabel("Frame Rate:")
        controls_layout.addWidget(fps_label)

        self.fps_combo = QComboBox()
        self.fps_combo.addItems(["24 fps", "25 fps", "29.97 fps", "30 fps"])
        self.fps_combo.setCurrentText("30 fps")
        self.fps_combo.setMinimumWidth(100)
        controls_layout.addWidget(self.fps_combo)

        controls_layout.addStretch()  # This now separates the left and right controls correctly

        # Right side - Open Output Folder button
        open_folder_btn = QPushButton("Open Output Folder")
        open_folder_btn.setMinimumWidth(180)  # Increased minimum width
        open_folder_btn.clicked.connect(self.open_export_folder)
        controls_layout.addWidget(open_folder_btn)

        # Wrap the controls in a QWidget for consistent alignment
        controls_container = QWidget()
        controls_container.setLayout(controls_layout)
        smpte_layout.addWidget(controls_container)

        # Processing Log
        log_group = QGroupBox("Processing Log")
        log_layout = QVBoxLayout()
        log_layout.setContentsMargins(12, 12, 12, 12)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(150)
        log_layout.addWidget(self.log_text)
        
        log_group.setLayout(log_layout)
        smpte_layout.addWidget(log_group)
        
        # --- Style lower section buttons (orange) ---
        orange_btn_style = """
            QPushButton {
                background: #FF9800;
                color: #222;
                border: none;
                border-radius: 4px;
                padding: 6px 18px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #FFB74D;
            }
            QPushButton:pressed {
                background: #F57C00;
            }
        """
        # Apply to lower section buttons
        self.select_file_btn.setStyleSheet(orange_btn_style)
        select_mapping_btn.setStyleSheet(orange_btn_style)
        edit_mapping_btn.setStyleSheet(orange_btn_style)
        create_mapping_btn.setStyleSheet(orange_btn_style)
        clear_mapping_btn.setStyleSheet(orange_btn_style)
        self.start_btn.setStyleSheet(orange_btn_style)
        open_folder_btn.setStyleSheet(orange_btn_style)
        
        smpte_group.setLayout(smpte_layout)
        main_layout.addWidget(smpte_group)
        
        # Load defaults
        self.load_defaults()
        self.update_filename_preview()
        
        # Set Application Icon
        icon_path = resource_path("icon.icns")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
    def update_filename_preview(self):
        """Update the filename preview based on current metadata"""
        date = self.date_edit.date().toString("yyyy.MM.dd")
        band = self.band_edit.text().strip()
        city = self.city_edit.text().strip()
        
        if band and city:
            base = f"{date}_{band}_{city}"
            self.filename_preview.setText(
                f"{base}_markers.csv\n"
                f"{base}_setlist.txt\n"
                f"{base}_detailed.txt"
            )
        else:
            self.filename_preview.setText("(Enter band and city)")
            
    def load_config(self) -> dict:
        """Load configuration including last used mapping file"""
        if not CONFIG_FILE.exists():
            return {}
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                logger.info(f"Loaded config from {CONFIG_FILE}")
                return config
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Error loading config file: {e}")
            return {}
            
    def save_config(self):
        """Save current configuration"""
        config = {
            'band': self.band_edit.text(),
            'city': self.city_edit.text(),
            'last_mapping_file': self.current_mapping_file_full_path if self.remember_mapping_checkbox.isChecked() else '',
            'export_folder': self.current_export_folder_full_path if self.remember_folder_checkbox.isChecked() else '',
            'remember_mapping': self.remember_mapping_checkbox.isChecked(),
            'remember_folder': self.remember_folder_checkbox.isChecked(),
        }
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=4)
            logger.info(f"Saved config to {CONFIG_FILE}")
        except Exception as e:
            logger.error(f"Error saving config file: {e}")
            
    def load_defaults(self):
        """Load default values from config file"""
        self.band_edit.setText(self.config.get('band', ''))
        self.city_edit.setText(self.config.get('city', ''))
        
        # Restore last mapping file if it exists and remember is checked
        last_mapping = self.config.get('last_mapping_file', '')
        remember_mapping = self.config.get('remember_mapping', False)
        if remember_mapping and last_mapping and Path(last_mapping).exists():
            self._update_mapping_path_label(last_mapping)
            self.log_text.append(f"Restored last mapping file: {Path(last_mapping).name}")
            self.remember_mapping_checkbox.setChecked(True)
        else:
            self.clear_mapping_file(log_event=False) # Clear without logging
            self.remember_mapping_checkbox.setChecked(False)
            
        # Restore export folder if it exists and remember is checked
        export_folder = self.config.get('export_folder', '')
        remember_folder = self.config.get('remember_folder', False)
        if remember_folder and export_folder and Path(export_folder).exists():
            self.update_path_display(self.export_folder_label, export_folder)
            self.current_export_folder_full_path = export_folder
            self.remember_folder_checkbox.setChecked(True)
        else:
            self.export_folder_label.setText("Default (same as application)")
            self.current_export_folder_full_path = os.getcwd()
            self.remember_folder_checkbox.setChecked(False)
            
    def save_defaults(self):
        """Save current values as defaults"""
        config = {
            'band': self.band_edit.text(),
            'city': self.city_edit.text()
        }
        with open('config.json', 'w') as f:
            json.dump(config, f)
            
    def select_audio_file(self):
        """Open file dialog to select audio file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Audio File",
            "",
            "Audio Files (*.wav *.aif *.aiff);;All Files (*.*)"
        )
        if file_path:
            self.update_path_display(self.file_path_label, file_path)
            self.current_audio_file_full_path = file_path
            self.log_text.append(f"Selected audio file: {Path(file_path).name}")
            
    def select_mapping_file(self):
        """Open file dialog to select SMPTE mapping file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select SMPTE Mapping File",
            "",
            "CSV Files (*.csv);;All Files (*.*)"
        )
        if file_path:
            try:
                # TODO: Load and validate mapping file
                self._update_mapping_path_label(file_path)
                self.log_text.append(f"Selected mapping file: {Path(file_path).name}")
                # Save the mapping file path in config if remember is checked
                if self.remember_mapping_checkbox.isChecked():
                    self.config['last_mapping_file'] = file_path
                    self.save_config()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load mapping file: {str(e)}")
                
    def open_mapping_editor(self, is_new_file: bool):
        """Open the mapping editor, either for a new file or to edit an existing one."""
        path_to_edit = None
        if is_new_file:
            logger.info("Opening mapping editor for a new file.")
        else:
            path_to_edit = self.current_mapping_file_full_path
            if not (path_to_edit and Path(path_to_edit).exists()):
                QMessageBox.warning(self, "No File", "Please select a mapping file to edit, or create a new one.")
                return
            logger.info(f"Opening mapping editor to edit file: '{path_to_edit}'")

        editor = SMPTEMappingEditor(parent=self, mapping_file_path=path_to_edit)
        
        # This will block until the editor is closed (Save or Cancel)
        if editor.exec():
            # This code runs ONLY if the user clicked "Save"
            if editor.mapping_file_path:
                new_path = editor.mapping_file_path
                logger.info(f"Mapping editor was saved. Path is now: '{new_path}'")
                self._update_mapping_path_label(new_path)
                
                # Save to config if the "remember" checkbox is ticked
                if self.remember_mapping_checkbox.isChecked():
                    self.config['last_mapping_file'] = new_path
                    self.save_config()
            else:
                logger.warning("Mapping editor was saved, but no file path was set. This may happen if saving a new file was cancelled.")

    def process_file(self):
        """Process the audio file for SMPTE timecodes"""
        audio_path = self.current_audio_file_full_path
        mapping_path = self.current_mapping_file_full_path
        export_folder = self.current_export_folder_full_path

        # Validate inputs
        if not audio_path or not Path(audio_path).exists():
            QMessageBox.warning(self, "Error", "Please select a valid audio file first.")
            return
            
        if not mapping_path or not Path(mapping_path).exists():
            QMessageBox.warning(self, "Error", "Please select a valid SMPTE mapping file.")
            return
            
        if not export_folder:
            export_folder = "." # Default to current directory

        # Update UI
        self.start_btn.setEnabled(False)
        self.select_file_btn.setEnabled(False)
        self.fps_combo.setEnabled(False)
        
        try:
            # Get FPS value
            fps = int(float(self.fps_combo.currentText().split()[0]))
            
            # Create detector and marker manager
            detector = SMPTEDetector(fps=fps)
            marker_manager = MarkerManager()
            
            # Process file -- these paths are now guaranteed to be full and valid
            
            # Generate output paths
            date = self.date_edit.date().toString("yyyy.MM.dd")
            band = self.band_edit.text().strip()
            city = self.city_edit.text().strip()
            base = f"{date}_{band}_{city}"
            
            # Use selected export folder or default
            markers_path = str(Path(export_folder) / f"{base}_markers.csv")
            setlist_path = str(Path(export_folder) / f"{base}_setlist.txt")
            detailed_path = str(Path(export_folder) / f"{base}_detailed.txt")
            
            # Check for existing files
            existing_files = []
            for path in [markers_path, setlist_path, detailed_path]:
                if Path(path).exists():
                    existing_files.append(path)
                    
            if existing_files:
                msg = "The following files already exist and will be overwritten:\n\n"
                msg += "\n".join(existing_files)
                msg += "\n\nDo you want to continue?"
                reply = QMessageBox.question(self, "Files Exist", msg, 
                                          QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                if reply == QMessageBox.StandardButton.No:
                    return
                    
            # Load the mapping file
            marker_manager.load_timecode_map(mapping_path)
            
            # Process and get results
            detected_markers = detector.process_file(
                audio_path,
                mapping_path,
                callback=self.update_progress
            )
            
            if detected_markers:
                # Add detected markers to marker manager
                # Invert the detected_markers dictionary to map timecodes to names
                timecode_to_name = {}
                for name, pos in detected_markers.items():
                    timecode = detector.format_time(pos)
                    timecode_to_name[timecode] = name
                
                # Add markers in the correct order
                for timecode, name in timecode_to_name.items():
                    marker_manager.add_marker(timecode, detected_markers[name], name)
                
                # Export in Reaper format
                marker_manager.export_reaper_csv(markers_path)
                        
                # Save setlist
                with open(setlist_path, 'w') as f:
                    for name, _ in sorted(detected_markers.items(), key=lambda x: x[1]):
                        f.write(f"{name}\n")
                        
                # Save detailed report
                with open(detailed_path, 'w') as f:
                    f.write("SMPTE Detection Report\n")
                    f.write("===================\n\n")
                    f.write(f"Audio File: {Path(audio_path).name}\n")
                    f.write(f"Frame Rate: {fps} fps\n\n")
                    f.write("Detected Markers:\n")
                    for name, pos in sorted(detected_markers.items(), key=lambda x: x[1]):
                        f.write(f"{detector.format_time(pos)} - {name}\n")
                        
                self.log_text.append("\nOutput files generated:")
                if existing_files:
                    self.log_text.append("(Overwriting existing files)")
                self.log_text.append(f"- {markers_path}")
                self.log_text.append(f"- {setlist_path}")
                self.log_text.append(f"- {detailed_path}")
                
                # Add button to open export folder
                open_folder_btn = QPushButton("Open Export Folder")
                open_folder_btn.clicked.connect(self.open_export_folder)
                open_folder_btn.setStyleSheet("""
                    QPushButton {
                        background: #2196F3;
                        color: white;
                        border: none;
                        border-radius: 4px;
                        padding: 5px 15px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background: #1976D2;
                    }
                    QPushButton:pressed {
                        background: #0D47A1;
                    }
                """)
                self.log_text.append("\n")
                self.log_text.append("<div style='text-align: center; margin: 10px 0;'>Open Export Folder</div>")
            else:
                self.log_text.append("\nNo markers found in the audio file.")
                self.log_text.append("Please check:")
                self.log_text.append("1. The audio file contains SMPTE timecode")
                self.log_text.append("2. The frame rate matches the timecode")
                self.log_text.append("3. The mapping file contains correct SMPTE codes")
                
        except Exception as e:
            self.log_text.append(f"\nError during processing: {str(e)}")
            QMessageBox.critical(self, "Error", f"Processing failed: {str(e)}")
            
        finally:
            # Re-enable controls
            self.start_btn.setEnabled(True)
            self.select_file_btn.setEnabled(True)
            self.fps_combo.setEnabled(True)
            
    def update_progress(self, message: str):
        """Update the progress log"""
        self.log_text.append(message)
        
    def select_export_folder(self):
        """Open folder dialog to select export location"""
        # Start from current export folder or app directory
        current_folder = self.export_folder_label.text()
        if current_folder == "Default (same as application)":
            current_folder = os.getcwd()
            
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "Select Export Folder",
            current_folder
        )
        if folder_path:
            self.update_path_display(self.export_folder_label, folder_path)
            self.current_export_folder_full_path = folder_path
            self.log_text.append(f"Export folder set to: {folder_path}")
            
    def open_export_folder(self):
        """Open the current export folder in system file explorer"""
        folder = self.current_export_folder_full_path
        if not folder or not Path(folder).exists():
            folder = os.getcwd()
            
        if platform.system() == "Windows":
            os.startfile(folder)
        elif platform.system() == "Darwin":  # macOS
            os.system(f"open {folder}")
        else:  # Linux
            os.system(f"xdg-open {folder}")
        
    def clear_mapping_file(self, log_event: bool = True):
        """Clear the current mapping file selection"""
        self.mapping_path_label.setText("No mapping file selected")
        self.mapping_path_label.setToolTip("")
        self.current_mapping_file_full_path = None
        if log_event:
            self.log_text.append("Cleared mapping file selection")
        # No need to save config here, let user action trigger save
        
    def update_path_display(self, label: QLabel, path: str, max_length: int = 60):
        """Update path display with ellipsis if too long"""
        if len(path) > max_length:
            # Keep the first part and last part, with ellipsis in middle
            parts = path.split(os.sep)
            if len(parts) > 4:
                shortened = os.sep.join(parts[:2] + ['...'] + parts[-2:])
            else:
                shortened = path[:max_length//2] + '...' + path[-max_length//2:]
            label.setText(shortened)
            label.setToolTip(path)  # Show full path on hover
        else:
            label.setText(path)
            label.setToolTip(path)
        
    def _update_mapping_path_label(self, path: str):
        """Update the mapping path label and the internal full path variable."""
        self.update_path_display(self.mapping_path_label, path)
        self.current_mapping_file_full_path = path
        
    def closeEvent(self, event):
        """Handle the window being closed."""
        self.save_config()
        super().closeEvent(event)
        
if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stdout,
    )
    
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec()) 