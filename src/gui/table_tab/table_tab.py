from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QSplitter, QVBoxLayout, QWidget

from .table_side_bar import TableSideBar
from .table_widget import TableWidget


class TableTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)

        self.splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self.layout.addWidget(self.splitter)

        self.table_side_bar = TableSideBar(self)
        self.splitter.addWidget(self.table_side_bar)

        self.table_widget = TableWidget(self)
        self.splitter.addWidget(self.table_widget)

        self.initialize_sizes()

    def initialize_sizes(self):
        total_width = self.width()
        side_bar_width = int(total_width / 5)
        table_width = int(total_width - side_bar_width)
        self.splitter.setSizes([side_bar_width, table_width])
