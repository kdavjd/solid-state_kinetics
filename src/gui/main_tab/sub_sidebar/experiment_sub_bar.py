from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (QComboBox, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QVBoxLayout, QWidget)


class SmoothingBlock(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayout(QVBoxLayout())

        self.smoothing_method = QComboBox()
        self.smoothing_method.addItems(["Савицкий-Голэй", "другой"])

        self.n_window = QLineEdit("1")
        self.n_poly = QLineEdit("0")
        self.spec_settings = QComboBox()
        self.spec_settings.addItems(["nearest", "другой"])

        self.apply_button = QPushButton("Применить")

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Метод сглаживания:"))
        layout.addWidget(self.smoothing_method)

        layout_n_window = QVBoxLayout()
        layout_n_window.addWidget(QLabel("n-окна:"))
        layout_n_window.addWidget(self.n_window)

        layout_n_poly = QVBoxLayout()
        layout_n_poly.addWidget(QLabel("n-полинома:"))
        layout_n_poly.addWidget(self.n_poly)

        h_layout = QHBoxLayout()
        h_layout.addLayout(layout_n_window)
        h_layout.addLayout(layout_n_poly)
        layout.addLayout(h_layout)

        layout.addWidget(QLabel("Специфические настройки:"))
        layout.addWidget(self.spec_settings)
        layout.addWidget(self.apply_button)
        self.layout().addLayout(layout)


class BackgroundSubtractionBlock(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayout(QVBoxLayout())

        self.background_method = QComboBox()
        self.background_method.addItems(["Линейная", "Сигмоидальная", "Тангенциальная",
                                         "Левая Тангенциальная", "Левая Сигмоидальная",
                                         "Правая Тангенциальная", "Правая Сигмоидальная", "Безье"])
        self.range_left = QLineEdit()
        self.range_right = QLineEdit()
        self.apply_button = QPushButton("Применить")

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Метод вычитания фона:"))
        layout.addWidget(self.background_method)

        layout.addWidget(QLabel("Диапазон вычитания фона:"))

        layout_range_left = QVBoxLayout()
        layout_range_left.addWidget(QLabel("Левая:"))
        layout_range_left.addWidget(self.range_left)

        layout_range_right = QVBoxLayout()
        layout_range_right.addWidget(QLabel("Правая:"))
        layout_range_right.addWidget(self.range_right)

        h_layout = QHBoxLayout()
        h_layout.addLayout(layout_range_left)
        h_layout.addLayout(layout_range_right)
        layout.addLayout(h_layout)

        layout.addWidget(self.apply_button)
        self.layout().addLayout(layout)


class ActionButtonsBlock(QWidget):
    cancel_changes_clicked = pyqtSignal(str)
    derivative_clicked = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayout(QVBoxLayout())

        self.cancel_changes_button = QPushButton("Отменить изменения")
        self.derivative_button = QPushButton("Привести к da/dT")

        self.cancel_changes_button.clicked.connect(
            lambda: self.cancel_changes_clicked.emit(self.cancel_changes_button.text()))
        self.derivative_button.clicked.connect(
            lambda: self.derivative_clicked.emit(self.derivative_button.text()))

        self.layout().addWidget(self.derivative_button)
        self.layout().addWidget(self.cancel_changes_button)


class ExperimentSubBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.smoothing_block = SmoothingBlock(self)
        self.background_subtraction_block = BackgroundSubtractionBlock(self)
        self.action_buttons_block = ActionButtonsBlock(self)

        layout.addWidget(self.smoothing_block)
        layout.addWidget(self.background_subtraction_block)
        layout.addWidget(self.action_buttons_block)

        self.updateGeometry()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.setMaximumWidth(self.parent().width())
