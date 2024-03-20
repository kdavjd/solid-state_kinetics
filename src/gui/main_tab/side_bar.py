from PyQt6.QtWidgets import QVBoxLayout, QWidget

from .load_file_button import LoadButton


class SideBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout()

        self.load_button = LoadButton("Загрузить", self)
        self.layout.addWidget(self.load_button)
        self.setLayout(self.layout)

