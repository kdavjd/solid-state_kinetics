from PyQt6.QtWidgets import (QMainWindow, QVBoxLayout,  # pylint: disable=E0611
                             QWidget)

from .plot_canvas import PlotCanvas
from .side_bar import SideBar


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Data Processing Application")
        self.setGeometry(100, 100, 800, 600)

        # Central Widget
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout()
        self.central_widget.setLayout(self.layout)

        # Plot Canvas
        self.plot_canvas = PlotCanvas(self, width=5, height=4)
        self.layout.addWidget(self.plot_canvas)

        # Sidebar
        self.sidebar = SideBar(self)
        self.layout.addWidget(self.sidebar)

    def public_method_1(self):
        pass

    def public_method_2(self):
        pass
