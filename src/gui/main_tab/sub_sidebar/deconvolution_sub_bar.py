from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (QHBoxLayout, QLabel, QListWidget, QMessageBox,
                             QPushButton, QVBoxLayout, QWidget)


class CalcButtons(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.start_button = QPushButton("Начать расчет")
        self.stop_button = QPushButton("Остановить расчет")
        self.layout.addWidget(self.start_button)

        self.start_button.clicked.connect(self.start_calculation)
        self.stop_button.clicked.connect(self.stop_calculation)
        self.is_calculating = False

    def start_calculation(self):
        self.is_calculating = True
        self.layout.replaceWidget(self.start_button, self.stop_button)
        self.start_button.hide()
        self.stop_button.show()

    def stop_calculation(self):
        self.is_calculating = False
        self.layout.replaceWidget(self.stop_button, self.start_button)
        self.stop_button.hide()
        self.start_button.show()


class ReactionTable(QWidget):
    reaction_added_signal = pyqtSignal(list, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)

        self.add_reaction_button = QPushButton("Добавить")
        self.load_reaction_button = QPushButton("Загрузить")
        self.top_buttons_layout = QHBoxLayout()
        self.top_buttons_layout.addWidget(self.add_reaction_button)
        self.top_buttons_layout.addWidget(self.load_reaction_button)
        self.layout.addLayout(self.top_buttons_layout)

        self.reactions_list = QListWidget()
        self.layout.addWidget(self.reactions_list)

        self.settings_button = QPushButton("Настройки")
        self.layout.addWidget(self.settings_button)

        self.add_reaction_button.clicked.connect(self.add_reaction)
        self.settings_button.clicked.connect(self.open_settings)

        self.reaction_counter = 0

    def add_reaction(self):
        reaction_name = f"реакция_{self.reaction_counter}"
        self.reactions_list.addItem(reaction_name)
        self.reaction_added_signal.emit([reaction_name], self.add_reaction_button.text())
        self.reaction_counter += 1

    def open_settings(self):
        if self.reactions_list.currentItem():
            reaction_details = self.reactions_list.currentItem().text()
            QMessageBox.information(self, "Настройки Реакции", f"Настройки для {reaction_details}")
        else:
            QMessageBox.warning(self, "Настройки Реакции", "Пожалуйста, выберите реакцию из списка.")


class DeconvolutionSubBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        self.calc_buttons = CalcButtons(self)
        self.reactions_table = ReactionTable(self)

        layout.addWidget(QLabel("Деконволюция"))
        layout.addWidget(self.calc_buttons)
        layout.addWidget(self.reactions_table)
