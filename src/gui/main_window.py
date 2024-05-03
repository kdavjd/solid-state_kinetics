from PyQt6.QtWidgets import QMainWindow, QTabWidget

from .main_tab.main_tab import MainTab
from .table_tab.table_tab import TableTab


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Кинетика твердофазных реакций")

        self.tabs = QTabWidget(self)
        self.setCentralWidget(self.tabs)

        self.main_tab = MainTab(self)
        self.table_tab = TableTab(self)

        self.tabs.addTab(self.main_tab, "Main")
        self.tabs.addTab(self.table_tab, "Table")
