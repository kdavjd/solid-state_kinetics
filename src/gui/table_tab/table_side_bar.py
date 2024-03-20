from PyQt6.QtWidgets import QVBoxLayout, QWidget


class TableSideBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout()
