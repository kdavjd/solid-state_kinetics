from os import path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QStandardItem, QStandardItemModel
from PyQt6.QtWidgets import QTreeView, QVBoxLayout, QWidget

from src.core.logger_config import logger

from .load_file_button import LoadButton


class SideBar(QWidget):
    file_selected = pyqtSignal(tuple)
    sub_side_bar_needed = pyqtSignal(str)
    chosen_experiment_signal = pyqtSignal(str)
    console_show_signal = pyqtSignal(bool)
    active_file_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout()

        self.tree_view = QTreeView()
        self.tree_view.clicked.connect(self.on_item_clicked)
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(["Управление проектом"])
        self.tree_view.setModel(self.model)

        self.experiments_data_root = QStandardItem("Данные экспериментов")
        self.add_data_item = QStandardItem("Добавить новые данные")
        self.model.appendRow(self.experiments_data_root)
        self.experiments_data_root.appendRow(self.add_data_item)

        self.model_free_root = QStandardItem("Безмодельный расчет")
        self.model.appendRow(self.model_free_root)
        self.model_free_root.appendRow(QStandardItem("Деконволюция"))
        self.model_free_root.appendRow(QStandardItem("Энергия активации"))
        self.model_free_root.appendRow(QStandardItem("Свободный коэффициент"))

        self.model_based_root = QStandardItem("Модельный расчет")
        self.model.appendRow(self.model_based_root)
        self.model_based_root.appendRow(QStandardItem("Добавить модель"))
        self.model_based_root.appendRow(QStandardItem("Импортировать модель"))

        self.settings_root = QStandardItem("Настройки")
        self.console_subroot = QStandardItem("Консоль")
        self.console_show_state = QStandardItem("Отобразить")
        self.console_show_state.setCheckable(True)
        self.console_show_state.setCheckState(Qt.CheckState.Checked)
        self.console_hide_state = QStandardItem("Скрыть")
        self.console_hide_state.setCheckable(True)
        self.model.appendRow(self.settings_root)
        self.settings_root.appendRow(self.console_subroot)
        self.console_subroot.appendRow(self.console_show_state)
        self.console_subroot.appendRow(self.console_hide_state)

        self.layout.addWidget(self.tree_view)
        self.setLayout(self.layout)

        self.load_button = LoadButton(self)
        self.load_button.file_selected.connect(self.add_experiment_file)

        self.active_file_item = None

    def mark_as_active(self, item):
        if self.active_file_item:
            self.unmark_active_state(self.active_file_item)
        self.mark_active_state(item)
        self.active_file_item = item
        self.active_file_selected.emit(item.text())
        logger.debug(f"Активный файл: {item.text()}")

    def mark_active_state(self, item):
        font = item.font()
        font.setBold(True)
        item.setFont(font)

    def unmark_active_state(self, item):
        font = item.font()
        font.setBold(False)
        item.setFont(font)

    def on_item_clicked(self, index):
        item = self.model.itemFromIndex(index)
        if item == self.add_data_item:
            self.load_button.open_file_dialog()
        elif item.parent() == self.experiments_data_root:
            self.sub_side_bar_needed.emit(item.text())
            self.chosen_experiment_signal.emit(item.text())
            self.mark_as_active(item)
        elif item == self.console_show_state:
            if item.checkState() == Qt.CheckState.Checked:
                self.console_show_signal.emit(True)
                self.console_hide_state.setCheckState(Qt.CheckState.Unchecked)
        elif item == self.console_hide_state:
            if item.checkState() == Qt.CheckState.Checked:
                self.console_show_signal.emit(False)
                self.console_show_state.setCheckState(Qt.CheckState.Unchecked)
        elif item.parent() == self.model_free_root:
            self.sub_side_bar_needed.emit(item.text())
        else:
            self.sub_side_bar_needed.emit("")

    def add_experiment_file(self, file_info):
        new_file_item = QStandardItem(path.basename(file_info[0]))
        self.experiments_data_root.insertRow(self.experiments_data_root.rowCount() - 1, new_file_item)
        self.tree_view.expandAll()
        self.mark_as_active(new_file_item)
        self.sub_side_bar_needed.emit(new_file_item.text())
        logger.debug(f"Новый файл добавлен и выбран активным: {new_file_item.text()}")

    def get_experiment_files_names(self) -> list[str]:
        files_names = []
        for row in range(self.experiments_data_root.rowCount() - 1):
            item = self.experiments_data_root.child(row)
            if item is not None:
                files_names.append(item.text())
        return files_names
