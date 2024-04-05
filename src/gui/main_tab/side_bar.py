from os import path

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QStandardItem, QStandardItemModel
from PyQt6.QtWidgets import QTreeView, QVBoxLayout, QWidget

from src.core.logger_config import logger

from .load_file_button import LoadButton


class SideBar(QWidget):
    file_selected = pyqtSignal(tuple)
    sub_side_bar_needed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout()

        self.tree_view = QTreeView()
        self.tree_view.clicked.connect(self.on_item_clicked)
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(["Управление проектом"])
        self.tree_view.setModel(self.model)

        self.experiments_data_root = QStandardItem("Данные экспериментов")
        self.model.appendRow(self.experiments_data_root)

        self.add_data_item = QStandardItem("Добавить новые данные")
        self.experiments_data_root.appendRow(self.add_data_item)

        self.calculation_root = QStandardItem("Безмодельный расчет")
        self.model.appendRow(self.calculation_root)

        self.calculation_root.appendRow(QStandardItem("Деконволюция"))
        self.calculation_root.appendRow(QStandardItem("Энергия активации"))
        self.calculation_root.appendRow(QStandardItem("Свободный коэффициент"))

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
            self.mark_as_active(item)
        elif item.parent() == self.calculation_root:
            self.sub_side_bar_needed.emit(item.text())
        else:
            self.sub_side_bar_needed.emit("")

    def add_experiment_file(self, file_info):
        new_file_item = QStandardItem(path.basename(file_info[0]))
        self.experiments_data_root.insertRow(self.experiments_data_root.rowCount() - 1, new_file_item)
        self.tree_view.expandAll()
        self.mark_as_active(new_file_item)
        logger.debug(f"New file added and marked as active: {new_file_item.text()}")
