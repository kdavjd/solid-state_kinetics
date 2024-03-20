from PyQt6.QtWidgets import QTextEdit, QVBoxLayout, QWidget

from src.logger_console import LoggerConsole


class ConsoleWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)

        layout = QVBoxLayout()
        layout.addWidget(self.text_edit)
        self.setLayout(layout)

        LoggerConsole.set_console(self)

    def log_message(self, message: str):
        self.text_edit.append(message)
