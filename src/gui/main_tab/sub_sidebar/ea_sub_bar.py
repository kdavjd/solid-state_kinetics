from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget


class AddSeriesDialog(QDialog):
    """Dialog for adding a new series name."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Введите название серии экспериментов")

        self.layout = QVBoxLayout(self)
        self.input_field = QLineEdit(self)
        self.input_field.setPlaceholderText("Название серии")
        self.layout.addWidget(self.input_field)

        # Adding OK and Cancel buttons
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.layout.addWidget(self.buttons)

    def get_series_name(self):
        """Returns the entered series name."""
        return self.input_field.text()


class EaSubBar(QWidget):
    create_series_signal = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.layout = QVBoxLayout(self)

        self.series_combobox = QComboBox(self)
        self.series_combobox.setPlaceholderText("Выберите серию экспериментов")
        self.layout.addWidget(self.series_combobox)

        self.merge_button = QPushButton("Создать новую серию", self)
        self.merge_button.clicked.connect(self.on_merge_dialog_button_pushed)
        self.layout.addWidget(self.merge_button)

        # Adding buttons and label for other functionalities
        self.layout.addWidget(QPushButton("Фридман", self))
        self.layout.addWidget(QPushButton("KAS/OFW/Starink", self))
        self.layout.addWidget(QPushButton("Вязовкин", self))
        self.layout.addWidget(QPushButton("Ортега", self))
        self.layout.addWidget(QLabel("Энергия активации", self))

    def open_merge_dialog(self):
        dialog = AddSeriesDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            series_name = dialog.get_series_name()
            if series_name:
                self.add_series(series_name)

    def on_merge_dialog_button_pushed(self):
        request = {"target": "calculations_data", "operation": "get_full_data"}
        self.create_series_signal.emit(request)

    def add_series(self, series_name):
        """Adds a new series name to the combo box and sets it as active."""
        self.series_combobox.addItem(series_name)
        self.series_combobox.setCurrentText(series_name)
