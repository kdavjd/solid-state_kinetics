from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import (QComboBox, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QVBoxLayout, QWidget)


class SmoothingBlock(QWidget):

    apply_clicked = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayout(QVBoxLayout())

        self.smoothing_method = QComboBox()
        self.smoothing_method.addItems(["Савицкий-Голэй", "Гаусса", "Средненего скользящего", "Медианный"])

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
        
        self.apply_button.clicked.connect(self.apply_smoothing)


        layout.addWidget(self.apply_button)
        self.layout().addLayout(layout)


    def apply_smoothing(self):
        method = self.smoothing_method.currentText()
        n_poly_value = int(self.n_poly.text())
        n_window_value = int(self.n_window.text())
        sigma = 3

        if method == "Савицкий-Голэй":
            self.apply_clicked.emit({'operation': "smooth", "method": "sav", "n_poly_value": n_poly_value, "n_window_value": n_window_value})
        elif method == "Гаусса":
            self.apply_clicked.emit({'operation': "smooth", "method": "gauss", "sigma_value": sigma})
        elif method == "Средненего скользящего":
            self.apply_clicked.emit({'operation': "smooth", "method": "mov", "window_size": n_window_value})
        elif method == "Медианный":
            self.apply_clicked.emit({'operation': "smooth", "method": "medi", "kernel_size": n_window_value})
            

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
    
    cancel_changes_clicked = pyqtSignal(dict)
    derivative_clicked = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayout(QVBoxLayout())

        self.cancel_changes_button = QPushButton("Отменить изменения")
        self.derivative_button = QPushButton("Привести к da/dT")

        self.derivative_button.clicked.connect(
            lambda: self.derivative_clicked.emit({'operation': "differential"}))
        
        self.cancel_changes_button.clicked.connect(
            lambda: self.cancel_changes_clicked.emit({'operation': "cancel_changes"}))

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
