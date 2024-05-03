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
    reaction_added_signal = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        add_reaction_button = QPushButton("Добавить")
        load_reaction_button = QPushButton("Загрузить")
        top_buttons_layout = QHBoxLayout()
        top_buttons_layout.addWidget(add_reaction_button)
        top_buttons_layout.addWidget(load_reaction_button)
        layout.addLayout(top_buttons_layout)

        self.reactions_list = QListWidget()
        layout.addWidget(self.reactions_list)

        settings_button = QPushButton("Настройки")
        layout.addWidget(settings_button)

        add_reaction_button.clicked.connect(self.add_reaction)
        settings_button.clicked.connect(self.open_settings)

        self.reaction_counter = 0

    def add_reaction(self):
        reaction_name = f"реакция_{self.reaction_counter}"
        self.reactions_list.addItem(reaction_name)
        self.reaction_added_signal.emit([reaction_name])
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
