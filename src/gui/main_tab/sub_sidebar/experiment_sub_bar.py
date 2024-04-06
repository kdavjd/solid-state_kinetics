from PyQt6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget


class ExperimentSubBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        layout.addWidget(QPushButton("Сгладить данные"))
        layout.addWidget(QPushButton("Вычесть фон"))
        layout.addWidget(QPushButton("Отменить изменения"))
        layout.addWidget(QLabel("Эксперимент"))
