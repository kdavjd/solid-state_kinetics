from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.gui.main_tab.sub_sidebar.model_based.models_scheme import ModelsScheme


class ModelBasedTab(QWidget):
    simulation_started = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)

        main_layout = QVBoxLayout(self)

        # Верхний ряд: кнопки settings и start
        buttons_layout = QHBoxLayout()
        settings_button = QPushButton("Settings")
        start_button = QPushButton("Start")
        buttons_layout.addWidget(settings_button)
        buttons_layout.addWidget(start_button)

        # Однострочное текстовое поле (для примера, пусть будет)
        line_edit = QLineEdit()

        # Виджет схемы реакций
        self.models_scene = ModelsScheme(self)

        main_layout.addLayout(buttons_layout)
        main_layout.addWidget(line_edit)
        main_layout.addWidget(self.models_scene)

        self.setLayout(main_layout)

        # Подключаем сигнал нажатия кнопки start
        start_button.clicked.connect(self.start_simulation)

    def start_simulation(self):
        scheme = self.models_scene.get_reaction_scheme_as_json()
        self.simulation_started.emit({"operation": "model_based_calculation", "scheme": scheme})

    def generate_ode_system(self, scheme):
        """
        Генерация системы дифференциальных уравнений из JSON схемы.
        Предположим, что:
        - Каждый узел - химический вид (A, B, C, ...).
        - Каждый переход (from -> to) - реакция первого порядка с собственной константой скорости k_from_to.
        - Для упрощения мы просто подставим символические константы скорости k_AB, k_BC и т.д.

        Уравнения вида:
        d[X]/dt = ∑(скорости образования X) - ∑(скорости расходования X)

        Скорость первой реакции from -> to: v = k_from_to * [from]
        """

        # Получаем список уникальных узлов
        nodes = [n["id"] for n in scheme["nodes"]]

        # Строим словарь исходящих реакций для каждого узла
        outgoing = {node: [] for node in nodes}
        # Строим словарь входящих реакций для каждого узла
        incoming = {node: [] for node in nodes}

        for edge in scheme["edges"]:
            f = edge["from"]
            t = edge["to"]
            outgoing[f].append(t)
            incoming[t].append(f)

        # Формируем уравнения
        equations = []
        for node in nodes:
            # Расход: все реакции, в которых node является "from"
            # v_out = Σ_k_from_node * [node]
            consumption_terms = []
            for to_node in outgoing[node]:
                rate_constant = f"k_{node}_{to_node}"
                consumption_terms.append(f"{rate_constant} * [{node}]")

            # Образование: все реакции, в которых node является "to"
            # v_in = Σ_k_from_node * [from_node]
            formation_terms = []
            for from_node in incoming[node]:
                rate_constant = f"k_{from_node}_{node}"
                formation_terms.append(f"{rate_constant} * [{from_node}]")

            # Формируем итоговое уравнение:
            # d[node]/dt = (sum of formation) - (sum of consumption)
            eq = f"d[{node}]/dt = "
            if formation_terms:
                eq += " + ".join(formation_terms)
            else:
                eq += "0"
            if consumption_terms:
                eq += " - (" + " + ".join(consumption_terms) + ")"
            equations.append(eq)

        return equations


class SelectFileDataDialog(QDialog):
    def __init__(self, df_copies, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Files for Series")
        self.selected_files = []
        self.checkboxes = []
        self.line_edits = []

        layout = QVBoxLayout()

        label = QLabel("Select files to include in the series:")
        layout.addWidget(label)

        self.series_name_line_edit = QLineEdit()
        self.series_name_line_edit.setPlaceholderText("Enter series name")
        layout.addWidget(self.series_name_line_edit)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout()

        for file_name in df_copies.keys():
            file_layout = QHBoxLayout()

            checkbox = QCheckBox(file_name)
            line_edit = QLineEdit()
            line_edit.setPlaceholderText("Enter heating rate")

            file_layout.addWidget(checkbox)
            file_layout.addWidget(line_edit)
            scroll_layout.addLayout(file_layout)

            self.checkboxes.append(checkbox)
            self.line_edits.append(line_edit)

        scroll_content.setLayout(scroll_layout)
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

        # Buttons
        button_box = QHBoxLayout()
        self.ok_button = QPushButton("OK")
        self.cancel_button = QPushButton("Cancel")
        button_box.addWidget(self.ok_button)
        button_box.addWidget(self.cancel_button)
        layout.addLayout(button_box)

        self.setLayout(layout)

        # Connect buttons
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

    def get_selected_files(self):
        series_name = self.series_name_line_edit.text().strip()
        if not series_name:
            QMessageBox.warning(self, "Invalid Input", "Please enter a series name.")
            return None, []

        selected_files = []
        for checkbox, line_edit in zip(self.checkboxes, self.line_edits):
            if checkbox.isChecked():
                rate_text = line_edit.text().strip()

                if not rate_text:
                    QMessageBox.warning(self, "Invalid Input", f"Please enter a heating rate for '{checkbox.text()}'")
                    return None, []

                try:
                    heating_rate = int(rate_text)
                except ValueError:
                    QMessageBox.warning(
                        self,
                        "Invalid Input",
                        f"Please enter a valid integer heating rate for '{checkbox.text()}'",
                    )
                    return None, []
                else:
                    selected_files.append((checkbox.text(), heating_rate))

        return series_name, selected_files
