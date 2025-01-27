from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.core.operation_enums import OperationType
from src.gui.main_tab.sub_sidebar.model_based.models_scheme import ModelsScheme


class ReactionTable(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(3, 4, parent)
        self.setHorizontalHeaderLabels(["Parameter", "Value", "Min", "Max"])
        self.setColumnHidden(2, True)
        self.setColumnHidden(3, True)

        # Ea
        self.setItem(0, 0, QTableWidgetItem("Ea"))  # Parameter
        self.activation_energy_edit = QLineEdit()
        self.setCellWidget(0, 1, self.activation_energy_edit)  # Value
        self.ea_min_item = QTableWidgetItem("")
        self.setItem(0, 2, self.ea_min_item)
        self.ea_max_item = QTableWidgetItem("")
        self.setItem(0, 3, self.ea_max_item)

        # log(A)
        self.setItem(1, 0, QTableWidgetItem("log(A)"))
        self.log_a_edit = QLineEdit()
        self.setCellWidget(1, 1, self.log_a_edit)
        self.log_a_min_item = QTableWidgetItem("")
        self.setItem(1, 2, self.log_a_min_item)
        self.log_a_max_item = QTableWidgetItem("")
        self.setItem(1, 3, self.log_a_max_item)

        # contribution
        self.setItem(2, 0, QTableWidgetItem("contribution"))
        self.contribution_edit = QLineEdit()
        self.setCellWidget(2, 1, self.contribution_edit)
        self.contribution_min_item = QTableWidgetItem("")
        self.setItem(2, 2, self.contribution_min_item)
        self.setItem(2, 3, QTableWidgetItem(""))
        self.contribution_max_item = QTableWidgetItem("")
        self.setItem(2, 3, self.contribution_max_item)

        self.default_ranges = {
            "Ea": (1000, 2000000),
            "log_A": (0.1, 100),
            "contribution": (0.01, 1),
        }

    def set_ranges_visible(self, visible: bool):
        self.setColumnHidden(2, not visible)
        self.setColumnHidden(3, not visible)

        if visible:
            ea_min, ea_max = self.default_ranges["Ea"]
            self.ea_min_item.setText(str(ea_min))
            self.ea_max_item.setText(str(ea_max))

            log_a_min, log_a_max = self.default_ranges["log_A"]
            self.log_a_min_item.setText(str(log_a_min))
            self.log_a_max_item.setText(str(log_a_max))

            contrib_min, contrib_max = self.default_ranges["contribution"]
            self.contribution_min_item.setText(str(contrib_min))
            self.contribution_max_item.setText(str(contrib_max))

    def update_table(self, reaction_data: dict):
        self.activation_energy_edit.setText(str(reaction_data.get("Ea", 120000)))
        self.log_a_edit.setText(str(reaction_data.get("log_A", 8)))
        self.contribution_edit.setText(str(reaction_data.get("contribution", 0.5)))

        ea_min = reaction_data.get("Ea_min", self.default_ranges["Ea"][0])
        ea_max = reaction_data.get("Ea_max", self.default_ranges["Ea"][1])
        self.ea_min_item.setText(str(ea_min))
        self.ea_max_item.setText(str(ea_max))

        log_a_min = reaction_data.get("log_A_min", self.default_ranges["log_A"][0])
        log_a_max = reaction_data.get("log_A_max", self.default_ranges["log_A"][1])
        self.log_a_min_item.setText(str(log_a_min))
        self.log_a_max_item.setText(str(log_a_max))

        contrib_min = reaction_data.get("contribution_min", self.default_ranges["contribution"][0])
        contrib_max = reaction_data.get("contribution_max", self.default_ranges["contribution"][1])
        self.contribution_min_item.setText(str(contrib_min))
        self.contribution_max_item.setText(str(contrib_max))


class ModelBasedTab(QWidget):
    simulation_started = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        main_layout = QVBoxLayout(self)
        self.setLayout(main_layout)

        reaction_type_layout = QHBoxLayout()
        reaction_type_label = QLabel("Reaction type:")
        self.reaction_type_combo = QComboBox()
        self.reaction_type_combo.addItems(["F1", "F2", "F3"])

        self.reactions_combo = QComboBox()
        main_layout.addWidget(self.reactions_combo)

        reaction_type_layout.addWidget(reaction_type_label)
        reaction_type_layout.addWidget(self.reaction_type_combo)
        main_layout.addLayout(reaction_type_layout)

        self.reaction_table = ReactionTable()
        main_layout.addWidget(self.reaction_table)

        self.show_range_checkbox = QCheckBox("Show Range")
        self.show_range_checkbox.stateChanged.connect(self.on_show_range_checkbox_changed)
        main_layout.addWidget(self.show_range_checkbox)

        bottom_layout = QVBoxLayout()
        buttons_layout = QHBoxLayout()
        settings_button = QPushButton("Settings")
        start_button = QPushButton("Start")
        buttons_layout.addWidget(settings_button)
        buttons_layout.addWidget(start_button)

        self.models_scene = ModelsScheme(self)
        bottom_layout.addLayout(buttons_layout)
        bottom_layout.addWidget(self.models_scene)
        main_layout.addLayout(bottom_layout)

        start_button.clicked.connect(self.start_simulation)

        self.update_reactions_combo_box()

    def on_show_range_checkbox_changed(self, state: int):
        self.reaction_table.set_ranges_visible(bool(state))

    def update_reactions_combo_box(self):
        self.reactions_combo.clear()
        scheme = self.models_scene.get_reaction_scheme_as_json()
        for reaction in scheme["reactions"]:
            parent_letter = reaction["from"]
            child_letter = reaction["to"]
            label = f"{parent_letter} -> {child_letter}"
            self.reactions_combo.addItem(label)

    def update_reaction_table(self, reaction_data: dict):
        self.reaction_table.update_table(reaction_data)

    def start_simulation(self):
        scheme = self.models_scene.get_reaction_scheme_as_json()

        # scheme["selected_reaction_type"] = self.reaction_type_combo.currentText()

        self.simulation_started.emit(
            {
                "operation": OperationType.MODEL_BASED_CALCULATION,
                "scheme": scheme,
            }
        )


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
