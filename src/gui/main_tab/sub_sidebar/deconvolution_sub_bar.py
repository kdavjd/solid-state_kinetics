from PyQt6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget


class DeconvolutionSubBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        layout.addWidget(QPushButton("Взять производную"))
        layout.addWidget(QPushButton("Начать расчет"))
        layout.addWidget(QPushButton("Остановить расчет"))
        layout.addWidget(QLabel("Деконволюция"))
