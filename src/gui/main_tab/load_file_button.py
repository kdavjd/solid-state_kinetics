import csv
import os

from PyQt6.QtCore import QSize, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from src.core.logger_config import logger


class LoadButton(QWidget):
    """
    A widget that provides functionality to load a file and emit its details.

    Signals:
        file_selected (tuple): Emitted when a file is selected with its parameters.
    """

    file_selected = pyqtSignal(tuple)

    file_extensions = "CSV files (*.csv);;Text files (*.txt)"

    def open_file_dialog(self):
        try:
            home_dir = os.getenv("HOME", "")
            file_path, _ = QFileDialog.getOpenFileName(self, "Open File", home_dir, self.file_extensions)
            if file_path:
                logger.debug("Selected file: %s", file_path)
                self.pre_load_dialog(file_path)
        except Exception as e:
            logger.error("Error loading file: %s", e)

    def pre_load_dialog(self, file_path):
        """
        Initializes and displays the PreLoadDialog. If the dialog is accepted,
        emits the file_selected signal with the file parameters.

        Args:
            file_path (str): The path of the selected file.
        """
        dialog = PreLoadDialog(file_path, self)
        if dialog.exec():
            self.file_selected.emit(
                (
                    dialog.file_path(),
                    dialog.delimiter(),
                    dialog.skip_rows(),
                    dialog.columns_names(),
                )
            )


class PreLoadDialog(QDialog):
    """
    A dialog for configuring file loading parameters such as delimiter,
    columns names, and rows to skip.

    Args:
        file_path (str): The path of the file to load.
        parent (QWidget, optional): The parent widget. Defaults to None.
    """

    def __init__(self, file_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("File Pre-Load Configuration")
        self.setFixedSize(QSize(400, 250))

        # Initialize input fields
        self.file_path_edit = QLineEdit(file_path)
        self.columns_names_edit = QLineEdit()
        self.columns_names_edit.setPlaceholderText("temperature, 3, 5, 10")

        self.delimiter_edit = QLineEdit(",")
        self.skip_rows_edit = QLineEdit("0")

        # Set up the layout
        layout = QVBoxLayout()

        layout.addWidget(QLabel("file path:"))
        layout.addWidget(self.file_path_edit)

        layout.addWidget(QLabel("column names:"))
        layout.addWidget(self.columns_names_edit)

        row_layout = QHBoxLayout()
        row_layout.addWidget(QLabel("delimiter:"))
        row_layout.addWidget(self.delimiter_edit)
        row_layout.addWidget(QLabel("rows to skip:"))
        row_layout.addWidget(self.skip_rows_edit)
        layout.addLayout(row_layout)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

        # Automatically update delimiter and skip rows based on file content
        self.auto_update_delimiter()
        self.auto_update_skip_rows()

        # Connect text change signals to update methods
        self.file_path_edit.textChanged.connect(self.auto_update_delimiter)
        self.delimiter_edit.textChanged.connect(self.auto_update_skip_rows)

    def file_path(self):
        return self.file_path_edit.text()

    def columns_names(self):
        if not self.columns_names_edit.text():
            return self.auto_extract_columns_names()
        return self.columns_names_edit.text()

    def delimiter(self):
        return self.delimiter_edit.text()

    def skip_rows(self):
        try:
            return int(self.skip_rows_edit.text())
        except ValueError:
            logger.error("Invalid number for rows to skip: %s", self.skip_rows_edit.text())
            return 0

    def auto_update_delimiter(self):
        """
        Automatically detects and updates the delimiter based on the file content.
        Logs the detected delimiter or an error if detection fails.
        """
        file_path = self.file_path()
        if not os.path.isfile(file_path):
            logger.error("Invalid file path: %s", file_path)
            return
        try:
            with open(file_path, "r", newline="", encoding="utf-8") as file:
                sample = file.read(1024)
                sniffer = csv.Sniffer()
                dialect = sniffer.sniff(sample)
                self.delimiter_edit.setText(dialect.delimiter)
                logger.debug('Detected delimiter: "%s"', dialect.delimiter)
        except csv.Error:
            logger.error("Failed to determine the delimiter")
        except Exception as e:
            logger.error("Error reading file for delimiter detection: %s", e)

    def is_data_line(self, line, delimiter):
        """
        Determines if a line contains data by attempting to parse numerical values.

        Args:
            line (str): The line to check.
            delimiter (str): The delimiter used in the file.

        Returns:
            bool: True if the line contains data, False otherwise.
        """
        try:
            parts = line.split(delimiter)
            # Attempt to convert the first two columns to float
            float(parts[0].replace(",", "."))
            float(parts[1].replace(",", "."))
            return True
        except (ValueError, IndexError):
            return False

    def auto_update_skip_rows(self):
        """
        Automatically determines the number of rows to skip by finding the first
        line that contains data. Logs the number of rows to skip or an error if
        detection fails.
        """
        file_path = self.file_path()
        delimiter = self.delimiter()
        if not os.path.isfile(file_path):
            logger.error("Invalid file path: %s", file_path)
            return
        try:
            with open(file_path, "r", newline="", encoding="utf-8") as file:
                for line_number, line in enumerate(file):
                    if self.is_data_line(line, delimiter):
                        self.skip_rows_edit.setText(str(line_number))
                        logger.debug("Determined number of rows to skip: %d", line_number)
                        return
            logger.error("Failed to determine the number of rows to skip")
        except Exception as e:
            logger.error("Error reading file for skip rows detection: %s", e)

    def auto_extract_columns_names(self):
        """
        Automatically extracts column names from the first line of the file.

        Returns:
            str: The extracted column names or an empty string if extraction fails.
        """
        file_path = self.file_path()
        if not os.path.isfile(file_path):
            logger.error("Invalid file path: %s", file_path)
            return ""
        try:
            with open(file_path, "r", newline="", encoding="utf-8") as file:
                first_line = file.readline().strip()
                if first_line:
                    logger.debug("Extracted column names: %s", first_line)
                    return first_line
        except Exception as e:
            logger.error("Error extracting column names: %s", e)
        return ""
