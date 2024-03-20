from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QSplitter, QVBoxLayout, QWidget

from ..console_widget import ConsoleWidget
from .plot_canvas import PlotCanvas
from .side_bar import SideBar


class MainTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)

        self.splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self.layout.addWidget(self.splitter)

        self.sidebar = SideBar(self)
        self.splitter.addWidget(self.sidebar)

        self.plot_canvas = PlotCanvas(self)
        self.splitter.addWidget(self.plot_canvas)

        self.console_widget = ConsoleWidget(self)
        self.splitter.addWidget(self.console_widget)

    def initialize_sizes(self):
        total_width = self.width()
        sidebar_width = int(total_width / 5)
        console_width = int(total_width / 5)
        canvas_width = int(total_width - sidebar_width - console_width)
        self.splitter.setSizes([sidebar_width, canvas_width, console_width])

    def showEvent(self, event):
        super().showEvent(event)
        self.initialize_sizes()