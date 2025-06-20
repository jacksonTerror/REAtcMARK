import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                           QHBoxLayout, QPushButton, QLabel, QFileDialog,
                           QTableWidget, QTableWidgetItem, QMessageBox,
                           QInputDialog, QLineEdit, QComboBox, QDialog,
                           QHeaderView)
from PyQt6.QtCore import Qt, QTime
from PyQt6.QtGui import QKeyEvent
import csv
import re
import timecode
from typing import Optional, List, Dict, Union, Any, cast
from pathlib import Path
import logging

# Set up logging for this module
logger = logging.getLogger(__name__)

class SMPTEInput(QLineEdit):
    """Custom QLineEdit for SMPTE timecode input with auto-formatting"""
    
    def __init__(self, parent: Optional[QDialog] = None):
        super().__init__(parent)
        self.setPlaceholderText("SMPTE (HH:MM:SS:FF)")
        self._formatting = False
        self.textChanged.connect(self._format_input)
        
    def _format_input(self):
        """Format input text as SMPTE timecode"""
        if self._formatting:
            return
            
        self._formatting = True
        cursor_pos = self.cursorPosition()
        
        # Get only numbers from input
        numbers = ''.join(filter(str.isdigit, self.text()))
        formatted = ""
        
        # Add numbers with colons after every 2 digits
        for i, num in enumerate(numbers[:8]):  # Limit to 8 digits
            if i > 0 and i % 2 == 0 and i < 8:
                formatted += ":"
            formatted += num
            
        # Calculate new cursor position
        # Count colons before the cursor
        colons_before = formatted[:cursor_pos].count(':')
        new_pos = cursor_pos + colons_before
        
        # If we just typed a number that should add a colon after it,
        # move the cursor one more position
        if cursor_pos > 0 and cursor_pos % 3 == 2 and cursor_pos < 8:
            new_pos += 1
            
        self.setText(formatted)
        self.setCursorPosition(min(new_pos, len(formatted)))
        self._formatting = False
        
    def keyPressEvent(self, event: QKeyEvent):
        """Handle key press events"""
        # Only allow numbers and basic editing keys
        if event.key() in (Qt.Key.Key_Backspace, Qt.Key.Key_Delete, Qt.Key.Key_Left, Qt.Key.Key_Right):
            super().keyPressEvent(event)
        elif event.text().isdigit():
            # Don't allow more than 8 digits
            numbers = ''.join(filter(str.isdigit, self.text()))
            if len(numbers) < 8:
                super().keyPressEvent(event)
        else:
            event.ignore()

class SMPTEMappingEditor(QDialog):
    def __init__(self, parent: Optional[QWidget] = None, mapping_file_path: Optional[str] = None):
        super().__init__(parent)
        self.setWindowTitle("SMPTE Mapping Editor")
        self.setMinimumSize(700, 500)
        self.mapping_file_path = mapping_file_path
        logger.info(f"MappingEditor initialized. File path: {self.mapping_file_path}")
        
        # Set dark theme colors
        dark_palette = """
            QDialog, QWidget {
                background: #2b2b2b;
                color: #e0e0e0;
            }
            QLineEdit {
                background: #363636;
                color: #e0e0e0;
                border: 1px solid #404040;
                border-radius: 4px;
                padding: 5px;
                min-height: 20px;
            }
            QLineEdit:focus {
                border: 1px solid #5294e2;
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
            QTableWidget {
                background: #363636;
                color: #e0e0e0;
                border: 1px solid #404040;
                border-radius: 4px;
                gridline-color: #404040;
            }
            QHeaderView::section {
                background: #2b2b2b;
                color: #e0e0e0;
                padding: 5px;
                border: 1px solid #404040;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QTableWidget::item:selected {
                background: #2c3e50;
                color: #e0e0e0;
            }
            QLabel {
                color: #e0e0e0;
            }
            QScrollBar:vertical {
                background: #2b2b2b;
                width: 14px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #404040;
                min-height: 20px;
                border-radius: 7px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """
        self.setStyleSheet(dark_palette)
        self.setup_ui()
        
        if self.mapping_file_path and Path(self.mapping_file_path).exists():
            self.load_mappings(self.mapping_file_path)
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Quick add section
        quick_add = QHBoxLayout()
        quick_add.setSpacing(8)
        
        self.smpte_edit = SMPTEInput()
        quick_add.addWidget(self.smpte_edit)
        
        self.marker_edit = QLineEdit()
        self.marker_edit.setPlaceholderText("Marker Name")
        quick_add.addWidget(self.marker_edit)
        
        add_btn = QPushButton("Add")
        add_btn.setStyleSheet("""
            QPushButton {
                background: #2e7d32;
                color: white;
                border: none;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #388e3c;
            }
            QPushButton:pressed {
                background: #1b5e20;
            }
        """)
        add_btn.clicked.connect(self.add_mapping)
        quick_add.addWidget(add_btn)
        
        layout.addLayout(quick_add)
        
        # Add keyboard shortcuts info
        shortcuts_label = QLabel("Shortcuts: Enter to add mapping, Tab to switch fields, Up/Down to navigate table")
        shortcuts_label.setStyleSheet("color: #808080; font-style: italic; margin-bottom: 8px;")
        layout.addWidget(shortcuts_label)
        
        # Mapping table
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["SMPTE Code", "Marker Name"])
        header = self.table.horizontalHeader()
        assert header is not None
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setStretchLastSection(True)
        vertical_header = self.table.verticalHeader()
        assert vertical_header is not None
        vertical_header.setVisible(False)
        
        # Disable auto-sorting on header click, but allow manual sort via button
        self.table.setSortingEnabled(False)
        layout.addWidget(self.table)
        
        # Button row
        button_row = QHBoxLayout()
        button_row.setSpacing(8)
        
        button_row.addStretch()
        
        delete_btn = QPushButton("Delete Selected")
        delete_btn.clicked.connect(self.delete_selected)
        button_row.addWidget(delete_btn)
        
        sort_btn = QPushButton("Sort by Time")
        sort_btn.clicked.connect(self.sort_mappings)
        button_row.addWidget(sort_btn)
        
        layout.addLayout(button_row)
        
        # Dialog buttons
        dialog_buttons = QHBoxLayout()
        dialog_buttons.setSpacing(8)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        dialog_buttons.addWidget(cancel_btn)
        
        save_btn = QPushButton("Save")
        save_btn.setStyleSheet("""
            QPushButton {
                background: #2196F3;
                color: white;
                border: none;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #1976D2;
            }
            QPushButton:pressed {
                background: #0D47A1;
            }
        """)
        save_btn.clicked.connect(self.accept)
        save_btn.setDefault(True)
        dialog_buttons.addWidget(save_btn)
        
        layout.addLayout(dialog_buttons)
        
        # Set up keyboard shortcuts
        self.marker_edit.returnPressed.connect(self.add_mapping)
        self.smpte_edit.returnPressed.connect(lambda: self.marker_edit.setFocus())
        
        # Set initial focus
        self.smpte_edit.setFocus()
        
    def validate_smpte(self, code: str) -> bool:
        """Validate SMPTE timecode format and values"""
        if not re.match(r'^\d{2}:\d{2}:\d{2}:\d{2}$', code):
            # Try to auto-format if it's just numbers
            numbers = ''.join(filter(str.isdigit, code))
            if len(numbers) == 8:
                formatted = f"{numbers[0:2]}:{numbers[2:4]}:{numbers[4:6]}:{numbers[6:8]}"
                return self.validate_smpte(formatted)
            return False
            
        try:
            hours, minutes, seconds, frames = map(int, code.split(':'))
            return (0 <= hours <= 23 and 
                   0 <= minutes <= 59 and 
                   0 <= seconds <= 59 and 
                   0 <= frames <= 29)  # Assuming 30fps
        except ValueError:
            return False
            
    def load_mappings(self, file_path: str):
        """Load mappings from a CSV file using the basic csv.reader."""
        logger.info(f"--- Loading Mappings using csv.reader from: {file_path} ---")
        mappings = []
        try:
            with open(file_path, mode='r', encoding='utf-8', newline='') as infile:
                reader = csv.reader(infile)
                
                # Skip header row, handle empty file
                try:
                    next(reader)
                except StopIteration:
                    logger.warning("CSV file is empty.")
                    self._populate_table([])
                    return

                for row_list in reader:
                    if len(row_list) >= 2:
                        smpte, name = row_list[0], row_list[1]
                        if smpte and name:
                            mappings.append({'SMPTE Code': smpte.strip(), 'Marker Name': name.strip()})
                    else:
                        logger.warning(f"Skipping malformed row: {row_list}")
            
            logger.info(f"Successfully parsed {len(mappings)} mappings.")
            self._populate_table(mappings)
            self.mapping_file_path = file_path
            self.setWindowTitle(f"SMPTE Mapping Editor - {Path(file_path).name}")

        except Exception as e:
            logger.error(f"Failed to load mappings with csv.reader: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to load mappings: {str(e)}")

    def _populate_table(self, mappings: List[Dict[str, str]]):
        """Clear the table and fill it with the given mappings."""
        logger.info(f"Populating table with {len(mappings)} mappings.")
        logger.debug(f"Data for table: {mappings}")
        
        # Use a more robust method for populating the table
        self.table.setRowCount(0)
        self.table.setRowCount(len(mappings))

        for row_index, mapping in enumerate(mappings):
            smpte_code = str(mapping.get('SMPTE Code', ''))
            marker_name = str(mapping.get('Marker Name', ''))

            logger.debug(f"Setting item at row {row_index}: {smpte_code}, {marker_name}")
            self.table.setItem(row_index, 0, QTableWidgetItem(smpte_code))
            self.table.setItem(row_index, 1, QTableWidgetItem(marker_name))

    def add_mapping(self):
        """Add a new mapping from the input fields to the table"""
        smpte_code = self.smpte_edit.text().strip()
        marker_name = self.marker_edit.text().strip()
        logger.info(f"Attempting to add mapping. SMPTE: '{smpte_code}', Name: '{marker_name}'")

        if not smpte_code or not marker_name:
            QMessageBox.warning(self, "Missing Information", "Both SMPTE code and marker name are required.")
            return

        if not self.validate_smpte(smpte_code):
            QMessageBox.warning(self, "Invalid SMPTE",
                                f"'{smpte_code}' is not a valid SMPTE code (HH:MM:SS:FF).")
            return

        # Check for duplicates
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.text() == smpte_code:
                QMessageBox.warning(self, "Duplicate SMPTE", f"The SMPTE code '{smpte_code}' already exists.")
                return

        # Add the new mapping to the table
        row_position = self.table.rowCount()
        self.table.insertRow(row_position)
        
        smpte_item = QTableWidgetItem(smpte_code)
        smpte_item.setFlags(smpte_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        marker_item = QTableWidgetItem(marker_name)

        self.table.setItem(row_position, 0, smpte_item)
        self.table.setItem(row_position, 1, marker_item)

        # Clear input fields and focus on SMPTE input
        self.smpte_edit.clear()
        self.marker_edit.clear()
        self.smpte_edit.setFocus()
        self.table.scrollToItem(marker_item)

    def delete_selected(self):
        """Delete the selected row(s) from the table"""
        selection_model = self.table.selectionModel()
        if not selection_model:
            return
            
        selected_rows = selection_model.selectedRows()
        # Sort rows in descending order to avoid index shifting issues
        for index in sorted(selected_rows, reverse=True):
            self.table.removeRow(index.row())

    def sort_mappings(self):
        """Sort the table by the SMPTE Code column"""
        self.table.sortItems(0, Qt.SortOrder.AscendingOrder)

    def get_mappings(self) -> List[Dict[str, str]]:
        """Extract all mappings from the table widget."""
        mappings = []
        for row in range(self.table.rowCount()):
            smpte_item = self.table.item(row, 0)
            marker_item = self.table.item(row, 1)
            
            if smpte_item and marker_item:
                smpte_code = smpte_item.text()
                marker_name = marker_item.text()
                if smpte_code and marker_name: # Ensure we don't save empty rows
                    mappings.append({"SMPTE Code": smpte_code, "Marker Name": marker_name})
        
        logger.debug(f"Extracted {len(mappings)} mappings from table: {mappings}")
        return mappings

    def accept(self):
        """Handle the Save action. Gets a file path if one doesn't exist."""
        logger.info(f"Save action initiated. Current file path: {self.mapping_file_path}")

        # If no path is set, we must get one from the user.
        if not self.mapping_file_path:
            logger.info("No file path set. Prompting user to select a save location.")
            file_path, _ = QFileDialog.getSaveFileName(self, "Save Mapping File", "", "CSV Files (*.csv)")
            
            if not file_path:
                logger.warning("User cancelled the save dialog. Aborting save.")
                return  # Do not close the dialog, let the user continue.
            
            self.mapping_file_path = file_path

        # By this point, self.mapping_file_path is guaranteed to be set.
        try:
            mappings = self.get_mappings()
            logger.debug(f"Saving {len(mappings)} mappings to {self.mapping_file_path}")
            
            with open(self.mapping_file_path, mode='w', newline='', encoding='utf-8') as outfile:
                writer = csv.writer(outfile)
                writer.writerow(['SMPTE Code', 'Marker Name'])
                for mapping in mappings:
                    writer.writerow([mapping['SMPTE Code'], mapping['Marker Name']])
            
            # If we successfully saved, call the parent's accept() to close the dialog.
            super().accept()

        except Exception as e:
            logger.error(f"Failed to save mappings: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to save mappings: {str(e)}")

    def keyPressEvent(self, event: QKeyEvent):
        """Handle key press events for shortcuts"""
        if event.key() == Qt.Key.Key_Delete and self.table.hasFocus():
            self.delete_selected()
        else:
            super().keyPressEvent(event)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    dialog = SMPTEMappingEditor()
    dialog.exec()
    sys.exit(app.exec()) 