from collections import defaultdict

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (QComboBox, QHBoxLayout, QHeaderView, QMessageBox,
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QVBoxLayout, QWidget)

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

        self.reactions_tables = {}
        self.reactions_counters = defaultdict(int)
        self.active_file = None
        self.active_reaction = ''

        self.settings_button = QPushButton("Настройки")
        self.layout.addWidget(self.settings_button)

        self.add_reaction_button.clicked.connect(self.add_reaction)
        self.del_reaction_button.clicked.connect(self.del_reaction)
        self.settings_button.clicked.connect(self.open_settings)

    def switch_file(self, file_name):
        if file_name not in self.reactions_tables:
            self.reactions_tables[file_name] = QTableWidget()
            self.reactions_tables[file_name].setColumnCount(2)
            self.reactions_tables[file_name].setHorizontalHeaderLabels(["Имя", "Функция"])
            self.reactions_tables[file_name].horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            self.reactions_tables[file_name].itemClicked.connect(self.selected_reaction)
            self.layout.addWidget(self.reactions_tables[file_name])

        if self.active_file:
            self.reactions_tables[self.active_file].setVisible(False)

        self.reactions_tables[file_name].setVisible(True)
        self.active_file = file_name

    def add_reaction(self):
        if not self.active_file:
            QMessageBox.warning(self, "Ошибка", "Файл не выбран.")
            return

        table = self.reactions_tables[self.active_file]
        row_count = table.rowCount()
        table.insertRow(row_count)

        reaction_name = f"reaction_{self.reactions_counters[self.active_file]}"
        combo = QComboBox()
        combo.addItems(["gauss", "frazer", "ads"])
        combo.setCurrentText("gauss")

        table.setItem(row_count, 0, QTableWidgetItem(reaction_name))
        table.setCellWidget(row_count, 1, combo)

        reaction_data = {
            "path_keys": [reaction_name],
            "operation": "add_reaction"
        }
        self.reaction_added.emit(reaction_data)
        self.reactions_counters[self.active_file] += 1

    def on_fail_add_reaction(self):
        if not self.active_file:
            logger.debug("Файл не выбран. Откат операции добавления невозможен.")
            return

        table = self.reactions_tables[self.active_file]
        if table.rowCount() > 0:
            last_row = table.rowCount() - 1
            table.removeRow(last_row)
            self.reactions_counters[self.active_file] -= 1
            logger.debug("Неудачное добавление реакции. Удалена последняя строка.")

    def del_reaction(self):
        if not self.active_file:
            QMessageBox.warning(self, "Удаление Реакции", "Файл не выбран.")
            return

        table = self.reactions_tables[self.active_file]
        if table.rowCount() > 0:
            last_row = table.rowCount() - 1
            item = table.item(last_row, 0)
            if item is not None:
                reaction_name = item.text()
                table.removeRow(last_row)
                self.reactions_counters[self.active_file] -= 1

                reaction_data = {
                    "path_keys": [reaction_name],
                    "operation": "remove_reaction"
                }
                self.reaction_removed.emit(reaction_data)
            else:
                logger.debug("Попытка удалить пустую ячейку.")
        else:
            QMessageBox.warning(self, "Удаление Реакции", "В списке нет реакций для удаления.")

    def selected_reaction(self, item):
        row = item.row()
        reaction_name = self.reactions_tables[self.active_file].item(row, 0).text()
        self.active_reaction = reaction_name
        logger.debug(f'Активная реакция: {reaction_name}')
        self.reaction_chosed.emit({
            "path_keys": [reaction_name],
            "operation": "highlight_reaction"
        })

    def open_settings(self):
        if self.active_file:
            table = self.reactions_tables[self.active_file]
            current_item = table.currentItem()
            if current_item:
                row = current_item.row()
                reaction_name = table.item(row, 0).text()
                QMessageBox.information(self, "Настройки Реакции", f"Настройки для {reaction_name}")
            else:
                QMessageBox.warning(self, "Настройки Реакции", "Пожалуйста, выберите реакцию из таблицы.")
        else:
            QMessageBox.warning(self, "Настройки Реакции", "Файл не выбран.")


class CoeffsTable(QTableWidget):
    update_value = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(6, 3, parent)
        self.header_labels = ['low', 'val', 'up']
        self.row_labels = ['h', 'z', 'w', 'fs', 'ads1', 'ads2']

        self.setHorizontalHeaderLabels(self.header_labels)
        self.setVerticalHeaderLabels(self.row_labels)
        self.mock_table()
        self.calculate_fixed_height()
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.cellChanged.connect(self.update_reaction_params)
        self._is_table_filling = False

    def calculate_fixed_height(self):
        row_height = self.rowHeight(0)
        borders_height = len(self.row_labels) * 2
        header_height = self.horizontalHeader().height()
        total_height = (row_height * len(self.row_labels)) + header_height + borders_height
        self.setFixedHeight(total_height)

    def mock_table(self):
        for i in range(len(self.row_labels)):
            for j in range(len(self.header_labels)):
                self.setItem(i, j, QTableWidgetItem("NaN"))

    def fill_table(self, reaction_params: dict):
        logger.debug(f"Приняты параметры реакции для таблицы {reaction_params}")
        param_keys = ['lower_bound_coeffs', 'coeffs', 'upper_bound_coeffs']
        self._is_filling = True
        for j, key in enumerate(param_keys):
            try:
                data = reaction_params[key][2]  # струтура ключей: x_range, function_type, params
                if len(data) > 6:
                    logger.error(f"Ошибка: Параметры реакции для '{key}' содержат больше 5 элементов.")
                    continue
                for i in range(min(6, len(data))):
                    value = f"{data[i]:.2f}"
                    self.setItem(i, j, QTableWidgetItem(value))
            except IndexError as e:
                logger.error(f"Ошибка индекса при обработке данных '{key}': {e}")
        self._is_filling = False

    def update_reaction_params(self, row, column):
        if not self._is_filling:
            try:
                item = self.item(row, column)
                value = float(item.text())
                row_label = self.verticalHeaderItem(row).text()
                column_label = self.horizontalHeaderItem(column).text()

                path_keys = [self.column_to_bound(column_label), row_label]
                data_change = {
                    'path_keys': path_keys,
                    'operation': 'update_value',
                    'value': value
                }
                self.update_value.emit(data_change)
            except ValueError as e:
                logger.error(f"Неверные данные для преобразования в число: ряд {row}, колонка {column}: {e}")

    def column_to_bound(self, column_label):
        return {
            'low': 'lower_bound_coeffs',
            'val': 'coeffs',
            'up': 'upper_bound_coeffs'
        }.get(column_label, '')


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
    update_value = pyqtSignal(dict)

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

        self.coeffs_table.update_value.connect(self.handle_update_value)

    def handle_update_value(self, data: dict):
        if self.reactions_table.active_reaction:
            data['path_keys'].insert(0, self.reactions_table.active_reaction)
        self.update_value.emit(data)
