from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (QHBoxLayout, QHeaderView, QListWidget,
                             QMessageBox, QPushButton, QTableWidget,
                             QTableWidgetItem, QVBoxLayout, QWidget)

from core.logger_config import logger


class FileTransferButtons(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)

        self.load_reactions_button = QPushButton("Импорт")
        self.export_reactions_button = QPushButton("Экспорт")
        self.buttons_layout = QHBoxLayout()
        self.buttons_layout.addWidget(self.load_reactions_button)
        self.buttons_layout.addWidget(self.export_reactions_button)
        self.layout.addLayout(self.buttons_layout)


class ReactionTable(QWidget):
    reaction_added = pyqtSignal(dict)
    reaction_removed = pyqtSignal(dict)
    reaction_chosed = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)

        self.add_reaction_button = QPushButton("Добавить")
        self.del_reaction_button = QPushButton("Удалить")
        self.top_buttons_layout = QHBoxLayout()
        self.top_buttons_layout.addWidget(self.add_reaction_button)
        self.top_buttons_layout.addWidget(self.del_reaction_button)
        self.layout.addLayout(self.top_buttons_layout)

        self.reactions_list = QListWidget()
        self.reactions_list.itemClicked.connect(self.selected_reaction)
        self.layout.addWidget(self.reactions_list)

        self.settings_button = QPushButton("Настройки")
        self.layout.addWidget(self.settings_button)

        self.add_reaction_button.clicked.connect(self.add_reaction)
        self.del_reaction_button.clicked.connect(self.del_reaction)
        self.settings_button.clicked.connect(self.open_settings)

        self.reaction_counter = 0

    def add_reaction(self):
        reaction_name = f"reaction_{self.reaction_counter}"
        self.reactions_list.addItem(reaction_name)
        reaction_data = {
            "path_keys": [reaction_name],
            "operation": "add_reaction"
        }
        self.reaction_added.emit(reaction_data)
        self.reaction_counter += 1
        logger.debug(
            f'Список реакций: {[self.reactions_list.item(i).text() for i in range(self.reactions_list.count())]}')

    def on_fail_add_reaction(self):
        if self.reactions_list.count() > 0:
            last_item_index = self.reactions_list.count() - 1
            last_item = self.reactions_list.item(last_item_index)
            self.reactions_list.takeItem(last_item_index)
            self.reaction_counter -= 1
            logger.debug(f"Неудачное добавление реакции. Удалён элемент: {last_item.text()}")

    def del_reaction(self):
        current_item = self.reactions_list.currentItem()
        if current_item is not None:
            reaction_name = current_item.text()
            row = self.reactions_list.row(current_item)
            self.reactions_list.takeItem(row)
            self.reaction_removed.emit({
                "path_keys": [reaction_name],
                "operation": "remove_reaction"
            })
            logger.debug(f"Создан запрос на удаление реакции: {reaction_name}")
        else:
            QMessageBox.warning(self, "Удаление Реакции", "Пожалуйста, выберите реакцию из списка для удаления.")

    def selected_reaction(self, item):
        logger.debug(f'Активная реакция: {item.text()}')
        self.reaction_chosed.emit({
            "path_keys": [item.text()],
            "operation": "highlight_reaction"
        })

    def open_settings(self):
        if self.reactions_list.currentItem():
            reaction_name = self.reactions_list.currentItem().text()
            QMessageBox.information(self, "Настройки Реакции", f"Настройки для {reaction_name}")
        else:
            QMessageBox.warning(self, "Настройки Реакции", "Пожалуйста, выберите реакцию из списка.")


class CoeffsTable(QTableWidget):

    def __init__(self, parent=None):
        super().__init__(5, 3, parent)
        self.setHorizontalHeaderLabels(['low', 'val', 'up'])
        self.setVerticalHeaderLabels(['h', 'z', 'w', 'a1', 'a2'])
        self.mock_table()

        row_height = self.rowHeight(0)
        borders_height = 10
        header_height = self.horizontalHeader().height()
        total_height = (row_height * 5) + header_height + borders_height
        self.setFixedHeight(total_height)

        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

    def mock_table(self):
        for i in range(5):
            for j in range(3):
                self.setItem(i, j, QTableWidgetItem(f"Mock,{i+1},{j+1}"))

    def fill_table(self, reaction_params: dict):
        logger.debug(f"Приняты параметры реакции для таблицы {reaction_params}")
        for j, key in enumerate(['lower_bound', 'value', 'upper_bound']):
            try:
                data = reaction_params[key][2]
                if len(data) > 5:
                    logger.error(f"Ошибка: Параметры реакции для '{key}' содержат больше 5 элементов.")
                    continue
                for i in range(5):
                    value = f"{data[i]:.2f}" if i < len(data) else "NaN"
                    self.setItem(i, j, QTableWidgetItem(value))
            except IndexError:
                logger.error(f"Ошибка индекса при обработке данных '{key}'.")
                continue


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


class DeconvolutionSubBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        self.reactions_table = ReactionTable(self)
        self.coeffs_table = CoeffsTable(self)
        self.file_transfer_buttons = FileTransferButtons(self)
        self.calc_buttons = CalcButtons(self)

        layout.addWidget(self.reactions_table)
        layout.addWidget(self.coeffs_table)
        layout.addWidget(self.file_transfer_buttons)
        layout.addWidget(self.calc_buttons)
