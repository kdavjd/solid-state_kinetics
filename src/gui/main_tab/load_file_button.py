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
    file_selected = pyqtSignal(tuple)

    file_extensions = "CSV files (*.csv);;Text files (*.txt)"

    def open_file_dialog(self):
        try:
            file_path, _ = QFileDialog.getOpenFileName(self, "Open File", os.getenv("HOME", ""), self.file_extensions)
            if file_path:
                logger.debug("Выбран файл: %s", file_path)
                self.pre_load_dialog(file_path)
        except Exception as e:
            logger.error("Ошибка при загрузке файла: %s", e)

    def pre_load_dialog(self, file_path):
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
    def __init__(self, file_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Предварительная настройка файла")
        self.setFixedSize(QSize(400, 250))

        self.file_path_edit = QLineEdit(file_path)
        self.columns_names_edit = QLineEdit()
        self.columns_names_edit.setPlaceholderText("temperature, 3, 5, 10")

        self.delimiter_edit = QLineEdit(",")
        self.skip_rows_edit = QLineEdit("0")

        layout = QVBoxLayout()

        layout.addWidget(QLabel("Путь к файла:"))
        layout.addWidget(self.file_path_edit)

        layout.addWidget(QLabel("Названия столбцов:"))
        layout.addWidget(self.columns_names_edit)

        row_layout = QHBoxLayout()
        row_layout.addWidget(QLabel("Разделитель:"))
        row_layout.addWidget(self.delimiter_edit)
        row_layout.addWidget(QLabel("Пропустить строк:"))
        row_layout.addWidget(self.skip_rows_edit)
        layout.addLayout(row_layout)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

        self.auto_update_delimeter()
        self.auto_update_skip_rows()

        self.file_path_edit.textChanged.connect(self.auto_update_delimeter)
        self.delimiter_edit.textChanged.connect(self.auto_update_skip_rows)

    def file_path(self):
        return self.file_path_edit.text()

    def columns_names(self):
        return self.columns_names_edit.text()

    def delimiter(self):
        return self.delimiter_edit.text()

    def skip_rows(self):
        return int(self.skip_rows_edit.text())

    def auto_update_delimeter(self):
        if not os.path.isfile(self.file_path()):
            logger.error("Некорректный путь к файлу")
            return
        try:
            with open(self.file_path(), "r") as file:
                data = file.read(1024)
                sniffer = csv.Sniffer()
                dialect = sniffer.sniff(data)
                self.delimiter_edit.setText(dialect.delimiter)
                logger.debug(f'Определён разделитель: "{dialect.delimiter}"')
        except csv.Error:
            logger.error("Не удалось определить разделить")

    def is_data_line(self, line, delimeter):
        try:
            parts = line.split(delimeter)
            float(parts[0].replace(",", "."))
            float(parts[1].replace(",", "."))
            return True
        except ValueError:
            return False

    def auto_update_skip_rows(self):
        if not os.path.isfile(self.file_path()):
            logger.error("Некорректный путь к файлу")
            return
        with open(self.file_path(), "r") as file:
            for line_number, line in enumerate(file):
                if self.is_data_line(line, self.delimiter()):
                    self.skip_rows_edit.setText(str(line_number))
                    logger.debug(f"Определено количество пропускаемых строк: {line_number}")
                    return
        logger.error("Не удалось определить количество пропускаемых строк")
