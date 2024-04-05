from PyQt6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget


class SubSideBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.current_widget = None

    def update_content(self, content_type):
        if self.current_widget is not None:
            self.layout.removeWidget(self.current_widget)
            self.current_widget.deleteLater()

        if content_type == "Деконволюция":
            self.current_widget = DeconvolutionSubBar(self)
        elif content_type == "Энергия активации":
            self.current_widget = EaSubBar(self)
        else:
            self.current_widget = QLabel("Неизвестный контент", self)

        self.layout.addWidget(self.current_widget)


class DeconvolutionSubBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        layout.addWidget(QPushButton("Взять производную"))
        layout.addWidget(QPushButton("Начать расчет"))
        layout.addWidget(QPushButton("Остановить расчет"))
        layout.addWidget(QLabel("Деконволюция"))


class EaSubBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        layout.addWidget(QPushButton("Фридман"))
        layout.addWidget(QPushButton("KAS/OFW/Starink"))
        layout.addWidget(QPushButton("Вязовкин"))
        layout.addWidget(QPushButton("Ортега"))
        layout.addWidget(QLabel("Энергия активации"))
