from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget


class SubSideBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.label = QLabel("Sub Side Bar")
        self.layout.addWidget(self.label)
