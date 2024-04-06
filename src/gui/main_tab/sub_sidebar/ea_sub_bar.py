from PyQt6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget


class EaSubBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        layout.addWidget(QPushButton("Фридман"))
        layout.addWidget(QPushButton("KAS/OFW/Starink"))
        layout.addWidget(QPushButton("Вязовкин"))
        layout.addWidget(QPushButton("Ортега"))
        layout.addWidget(QLabel("Энергия активации"))
