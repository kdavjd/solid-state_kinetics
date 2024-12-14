from gui.main_tab.sub_sidebar.model_based.models_scheme import ModelsScheme
from PyQt6.QtWidgets import QHBoxLayout, QLineEdit, QPushButton, QVBoxLayout, QWidget


class ModelBasedTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        main_layout = QVBoxLayout(self)

        # Верхний ряд: две кнопки в линию
        buttons_layout = QHBoxLayout()
        button1 = QPushButton("Button 1")
        button2 = QPushButton("Button 2")
        buttons_layout.addWidget(button1)
        buttons_layout.addWidget(button2)

        # Однострочное текстовое поле
        line_edit = QLineEdit()

        # Виджет ModelsScene внизу
        models_scene = ModelsScheme(self)

        # Добавляем всё в основной лэйаут
        main_layout.addLayout(buttons_layout)
        main_layout.addWidget(line_edit)
        main_layout.addWidget(models_scene)
