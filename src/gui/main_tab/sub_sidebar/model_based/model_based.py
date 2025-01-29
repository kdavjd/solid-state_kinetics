from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
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
        self.setItem(0, 0, QTableWidgetItem("Ea, kJ"))
        self.activation_energy_edit = QLineEdit()
        self.setCellWidget(0, 1, self.activation_energy_edit)
        self.ea_min_item = QLineEdit()
        self.setCellWidget(0, 2, self.ea_min_item)
        self.ea_max_item = QLineEdit()
        self.setCellWidget(0, 3, self.ea_max_item)

        # log(A)
        self.setItem(1, 0, QTableWidgetItem("log(A)"))
        self.log_a_edit = QLineEdit()
        self.setCellWidget(1, 1, self.log_a_edit)
        self.log_a_min_item = QLineEdit()
        self.setCellWidget(1, 2, self.log_a_min_item)
        self.log_a_max_item = QLineEdit()
        self.setCellWidget(1, 3, self.log_a_max_item)

        # Contribution
        self.setItem(2, 0, QTableWidgetItem("contribution"))
        self.contribution_edit = QLineEdit()
        self.setCellWidget(2, 1, self.contribution_edit)
        self.contribution_min_item = QLineEdit()
        self.setCellWidget(2, 2, self.contribution_min_item)
        self.contribution_max_item = QLineEdit()
        self.setCellWidget(2, 3, self.contribution_max_item)

        self.default_ranges = {
            "Ea": (1, 2000),
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
        if not reaction_data:
            self.activation_energy_edit.clear()
            self.log_a_edit.clear()
            self.contribution_edit.clear()
            self.ea_min_item.clear()
            self.ea_max_item.clear()
            self.log_a_min_item.clear()
            self.log_a_max_item.clear()
            self.contribution_min_item.clear()
            self.contribution_max_item.clear()
            return

        self.activation_energy_edit.setText(str(reaction_data.get("Ea", 120)))
        self.log_a_edit.setText(str(reaction_data.get("log_A", 8)))
        self.contribution_edit.setText(str(reaction_data.get("contribution", 0.5)))

        self.ea_min_item.setText(str(reaction_data.get("Ea_min", self.default_ranges["Ea"][0])))
        self.ea_max_item.setText(str(reaction_data.get("Ea_max", self.default_ranges["Ea"][1])))

        self.log_a_min_item.setText(str(reaction_data.get("log_A_min", self.default_ranges["log_A"][0])))
        self.log_a_max_item.setText(str(reaction_data.get("log_A_max", self.default_ranges["log_A"][1])))

        self.contribution_min_item.setText(
            str(reaction_data.get("contribution_min", self.default_ranges["contribution"][0]))
        )
        self.contribution_max_item.setText(
            str(reaction_data.get("contribution_max", self.default_ranges["contribution"][1]))
        )


class ModelBasedTab(QWidget):
    simulation_started = pyqtSignal(dict)
    model_params_changed = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scheme_data = {}
        self._reactions_list = []

        main_layout = QVBoxLayout(self)
        self.setLayout(main_layout)

        self.reactions_combo = QComboBox()
        main_layout.addWidget(self.reactions_combo)

        reaction_type_layout = QHBoxLayout()
        reaction_type_label = QLabel("Reaction type:")
        self.reaction_type_combo = QComboBox()
        self.reaction_type_combo.addItems(["F1", "F2", "F3"])

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
        self.settings_button = QPushButton("Settings")
        self.start_button = QPushButton("Start")
        buttons_layout.addWidget(self.settings_button)
        self.settings_button.clicked.connect(self.open_settings)
        buttons_layout.addWidget(self.start_button)

        self.models_scene = ModelsScheme(self)
        bottom_layout.addLayout(buttons_layout)
        bottom_layout.addWidget(self.models_scene)
        main_layout.addLayout(bottom_layout)

        self.start_button.clicked.connect(self.start_simulation)

        self.reaction_table.activation_energy_edit.editingFinished.connect(self._on_params_changed)
        self.reaction_table.log_a_edit.editingFinished.connect(self._on_params_changed)
        self.reaction_table.contribution_edit.editingFinished.connect(self._on_params_changed)
        self.reaction_table.ea_min_item.editingFinished.connect(self._on_params_changed)
        self.reaction_table.ea_max_item.editingFinished.connect(self._on_params_changed)
        self.reaction_table.log_a_min_item.editingFinished.connect(self._on_params_changed)
        self.reaction_table.log_a_max_item.editingFinished.connect(self._on_params_changed)
        self.reaction_table.contribution_min_item.editingFinished.connect(self._on_params_changed)
        self.reaction_table.contribution_max_item.editingFinished.connect(self._on_params_changed)

        self.reaction_type_combo.currentIndexChanged.connect(self._on_params_changed)
        self.reactions_combo.currentIndexChanged.connect(self._on_reactions_combo_changed)

    def on_show_range_checkbox_changed(self, state: int):
        self.reaction_table.set_ranges_visible(bool(state))

    def start_simulation(self):
        scheme = self.models_scene.get_reaction_scheme_as_json()
        self.simulation_started.emit(
            {
                "operation": OperationType.MODEL_BASED_CALCULATION,
                "scheme": scheme,
            }
        )

    def load_scheme_data(self, scheme_data: dict):
        old_from, old_to = None, None
        if self.reactions_combo.count() > 0:
            current_label = self.reactions_combo.currentText()
            if "->" in current_label:
                parts = current_label.split("->")
                old_from, old_to = parts[0].strip(), parts[1].strip()

        self._scheme_data = scheme_data
        self._reactions_list = scheme_data.get("reactions", [])

        self.reactions_combo.clear()
        reaction_map = {}  # label -> (index, reaction_data)
        for i, reaction in enumerate(self._reactions_list):
            label = f"{reaction.get('from', '?')} -> {reaction.get('to', '?')}"
            self.reactions_combo.addItem(label)
            reaction_map[label] = (i, reaction)

        new_index = None
        if old_from and old_to:
            old_label = f"{old_from} -> {old_to}"
            if old_label in reaction_map:
                new_index = reaction_map[old_label][0]

        default_label = "A -> B"
        if new_index is None and default_label in reaction_map:
            new_index = reaction_map[default_label][0]

        if new_index is None and len(self._reactions_list) > 0:
            new_index = 0

        if new_index is not None:
            self.reactions_combo.setCurrentIndex(new_index)
            self._on_reactions_combo_changed(new_index)
        else:
            self.reaction_table.update_table({})

    def _on_reactions_combo_changed(self, index: int):
        if 0 <= index < len(self._reactions_list):
            reaction_data = self._reactions_list[index]
            self.reaction_table.update_table(reaction_data)

            new_reaction_type = reaction_data.get("reaction_type", "F1")
            current_reaction_type = self.reaction_type_combo.currentText()

            if new_reaction_type != current_reaction_type:
                # to avoid recursuion problem, block signals
                was_blocked = self.reaction_type_combo.blockSignals(True)
                self.reaction_type_combo.setCurrentText(new_reaction_type)
                self.reaction_type_combo.blockSignals(was_blocked)
        else:
            self.reaction_table.update_table({})

    @pyqtSlot()
    def _on_params_changed(self):  # noqa: C901
        current_index = self.reactions_combo.currentIndex()
        if not (0 <= current_index < len(self._reactions_list)):
            return

        from_comp = self._reactions_list[current_index].get("from")
        to_comp = self._reactions_list[current_index].get("to")
        reaction_type = self.reaction_type_combo.currentText()

        try:
            ea_val = float(self.reaction_table.activation_energy_edit.text())
        except ValueError:
            ea_val = 120

        try:
            loga_val = float(self.reaction_table.log_a_edit.text())
        except ValueError:
            loga_val = 8

        try:
            contrib_val = float(self.reaction_table.contribution_edit.text())
        except ValueError:
            contrib_val = 0.5

        try:
            ea_min_val = float(self.reaction_table.ea_min_item.text())
        except ValueError:
            ea_min_val = self.reaction_table.default_ranges["Ea"][0]  # 1

        try:
            ea_max_val = float(self.reaction_table.ea_max_item.text())
        except ValueError:
            ea_max_val = self.reaction_table.default_ranges["Ea"][1]  # 2000

        try:
            loga_min_val = float(self.reaction_table.log_a_min_item.text())
        except ValueError:
            loga_min_val = self.reaction_table.default_ranges["log_A"][0]  # 0.1

        try:
            loga_max_val = float(self.reaction_table.log_a_max_item.text())
        except ValueError:
            loga_max_val = self.reaction_table.default_ranges["log_A"][1]  # 100

        try:
            contrib_min_val = float(self.reaction_table.contribution_min_item.text())
        except ValueError:
            contrib_min_val = self.reaction_table.default_ranges["contribution"][0]  # 0.01

        try:
            contrib_max_val = float(self.reaction_table.contribution_max_item.text())
        except ValueError:
            contrib_max_val = self.reaction_table.default_ranges["contribution"][1]  # 1

        new_scheme = self._scheme_data.copy()

        for r in new_scheme.get("reactions", []):
            if r.get("from") == from_comp and r.get("to") == to_comp:
                r["reaction_type"] = reaction_type
                r["Ea"] = ea_val
                r["log_A"] = loga_val
                r["contribution"] = contrib_val

                r["Ea_min"] = ea_min_val
                r["Ea_max"] = ea_max_val
                r["log_A_min"] = loga_min_val
                r["log_A_max"] = loga_max_val
                r["contribution_min"] = contrib_min_val
                r["contribution_max"] = contrib_max_val
                break

        update_data = {"operation": OperationType.MODEL_PARAMS_CHANGE, "reaction_scheme": new_scheme}
        self.model_params_changed.emit(update_data)

    def open_settings(self):
        if not self._reactions_list:
            QMessageBox.information(self, "No Reactions", "There are no available reactions to configure.")
            return

        dialog = CalculationSettingsDialog(self._reactions_list, parent=self)
        if dialog.exec():
            de_params, updated_reactions = dialog.get_data()

            self._reactions_list = updated_reactions

            if self._scheme_data and "reactions" in self._scheme_data:
                for i, r in enumerate(self._scheme_data["reactions"]):
                    if i < len(updated_reactions):
                        self._scheme_data["reactions"][i] = updated_reactions[i]

            update_data = {
                "operation": OperationType.MODEL_PARAMS_CHANGE,
                "reaction_scheme": self._scheme_data,
            }
            self.model_params_changed.emit(update_data)

            QMessageBox.information(self, "Settings Saved", "The settings have been updated successfully.")
        else:
            pass


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


class CalculationSettingsDialog(QDialog):
    def __init__(self, reactions_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Calculation Settings")

        self.reactions_data = reactions_data or []

        self.de_params_edits = {}

        main_layout = QHBoxLayout(self)
        self.setLayout(main_layout)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_widget.setLayout(left_layout)
        main_layout.addWidget(left_widget)

        method_label = QLabel("Calculation method:")
        self.calculation_method_combo = QComboBox()
        self.calculation_method_combo.addItems(["differential_evolution", "another_method"])
        self.calculation_method_combo.setCurrentText("differential_evolution")
        self.calculation_method_combo.currentTextChanged.connect(self.update_method_parameters)
        left_layout.addWidget(method_label)
        left_layout.addWidget(self.calculation_method_combo)

        self.de_group = QGroupBox("Differential Evolution Settings")
        self.de_layout = QFormLayout()
        self.de_group.setLayout(self.de_layout)
        left_layout.addWidget(self.de_group, stretch=0)

        for param_name, default_value in DIFFERENTIAL_EVOLUTION_DEFAULT_KWARGS.items():
            label = QLabel(param_name)
            label.setToolTip(self.get_tooltip_for_parameter(param_name))

            if isinstance(default_value, bool):
                edit_widget = QCheckBox()
                edit_widget.setChecked(default_value)
            elif param_name in ["strategy", "init", "updating"]:
                edit_widget = QComboBox()
                edit_widget.addItems(self.get_options_for_parameter(param_name))
                edit_widget.setCurrentText(str(default_value))
            else:
                text_val = str(default_value) if default_value is not None else "None"
                edit_widget = QLineEdit(text_val)

            self.de_params_edits[param_name] = edit_widget
            self.de_layout.addRow(label, edit_widget)

        left_layout.addStretch(1)

        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_widget.setLayout(right_layout)
        main_layout.addWidget(right_widget, stretch=1)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        right_layout.addWidget(scroll_area)

        scroll_content = QWidget()
        scroll_area.setWidget(scroll_content)

        self.reactions_grid = QGridLayout(scroll_content)
        scroll_content.setLayout(self.reactions_grid)

        self.reaction_boxes = []

        for i, reaction in enumerate(self.reactions_data):
            row = i % 2
            col = i // 2

            box_widget = QWidget()
            box_layout = QVBoxLayout(box_widget)
            box_widget.setLayout(box_layout)

            top_line_widget = QWidget()
            top_line_layout = QHBoxLayout(top_line_widget)
            top_line_widget.setLayout(top_line_layout)

            reaction_label = QLabel(f"{reaction.get('from', '?')} -> {reaction.get('to', '?')}")
            top_line_layout.addWidget(reaction_label)

            combo_type = QComboBox()
            combo_type.addItems(["F1", "F2", "F3"])
            current_type = reaction.get("reaction_type", "F1")
            if current_type in ["F1", "F2", "F3"]:
                combo_type.setCurrentText(current_type)
            top_line_layout.addWidget(combo_type)

            box_layout.addWidget(top_line_widget)

            table = QTableWidget(3, 2, self)
            table.setHorizontalHeaderLabels(["Min", "Max"])
            table.setVerticalHeaderLabels(["Ea", "log(A)", "contribution"])
            table.setEditTriggers(QAbstractItemView.EditTrigger.AllEditTriggers)
            table.verticalHeader().setVisible(True)
            table.horizontalHeader().setVisible(True)
            box_layout.addWidget(table)

            ea_min = str(reaction.get("Ea_min", 1))
            ea_max = str(reaction.get("Ea_max", 2000))
            table.setItem(0, 0, QTableWidgetItem(ea_min))
            table.setItem(0, 1, QTableWidgetItem(ea_max))

            log_a_min = str(reaction.get("log_A_min", 0.1))
            log_a_max = str(reaction.get("log_A_max", 100))
            table.setItem(1, 0, QTableWidgetItem(log_a_min))
            table.setItem(1, 1, QTableWidgetItem(log_a_max))

            contrib_min = str(reaction.get("contribution_min", 0.01))
            contrib_max = str(reaction.get("contribution_max", 1.0))
            table.setItem(2, 0, QTableWidgetItem(contrib_min))
            table.setItem(2, 1, QTableWidgetItem(contrib_max))

            self.reactions_grid.addWidget(box_widget, row, col)
            self.reaction_boxes.append((combo_type, table, reaction_label))

        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        right_layout.addWidget(btn_box)

        self.update_method_parameters()

    def update_method_parameters(self):
        selected_method = self.calculation_method_combo.currentText()
        if selected_method == "differential_evolution":
            self.de_group.setVisible(True)
        else:
            self.de_group.setVisible(False)

    def get_data(self):  # noqa: C901
        selected_method = self.calculation_method_combo.currentText()
        errors = []
        method_params = {}

        if selected_method == "differential_evolution":
            for key, widget in self.de_params_edits.items():
                if isinstance(widget, QCheckBox):
                    value = widget.isChecked()
                elif isinstance(widget, QComboBox):
                    value = widget.currentText()
                else:
                    text = widget.text().strip()
                    default_value = DIFFERENTIAL_EVOLUTION_DEFAULT_KWARGS[key]
                    value = self.convert_to_type(text, default_value)

                is_valid, error_msg = self.validate_parameter(key, value)
                if not is_valid:
                    errors.append(f"Parameter '{key}': {error_msg}")
                method_params[key] = value

        elif selected_method == "another_method":
            method_params = {"info": "No additional params set for another_method"}

        if errors:
            QMessageBox.warning(self, "Invalid DE parameters", "\n".join(errors))
            return None, None

        updated_reactions = []
        for (combo_type, table, label_reaction), old_reaction in zip(self.reaction_boxes, self.reactions_data):
            ea_min_str = table.item(0, 0).text().strip()
            ea_max_str = table.item(0, 1).text().strip()
            loga_min_str = table.item(1, 0).text().strip()
            loga_max_str = table.item(1, 1).text().strip()
            contrib_min_str = table.item(2, 0).text().strip()
            contrib_max_str = table.item(2, 1).text().strip()

            def safe_cast(s, default):
                try:
                    return float(s)
                except ValueError:
                    return default

            new_r = dict(old_reaction)
            new_r["reaction_type"] = combo_type.currentText()

            new_r["Ea_min"] = safe_cast(ea_min_str, old_reaction.get("Ea_min", 1))
            new_r["Ea_max"] = safe_cast(ea_max_str, old_reaction.get("Ea_max", 2000))
            new_r["log_A_min"] = safe_cast(loga_min_str, old_reaction.get("log_A_min", 0.1))
            new_r["log_A_max"] = safe_cast(loga_max_str, old_reaction.get("log_A_max", 100))
            new_r["contribution_min"] = safe_cast(contrib_min_str, old_reaction.get("contribution_min", 0.01))
            new_r["contribution_max"] = safe_cast(contrib_max_str, old_reaction.get("contribution_max", 1.0))

            updated_reactions.append(new_r)

        return {"method": selected_method, "parameters": method_params}, updated_reactions

    def accept(self):
        data_result, reactions = self.get_data()
        if data_result is None or reactions is None:
            return

        if data_result["method"] == "differential_evolution":
            params = data_result["parameters"]
            try:
                popsize_val = float(params.get("popsize", 15))
                maxiter_val = float(params.get("maxiter", 1000))
                if popsize_val <= 0 or maxiter_val <= 0:
                    QMessageBox.warning(self, "Invalid parameters", "popsize и maxiter должны быть > 0.")
                    return
            except Exception:
                QMessageBox.warning(self, "Invalid parameters", "Не удалось прочитать popsize/maxiter корректно.")
                return

        super().accept()

    def convert_to_type(self, text, default_value):
        if text.lower() == "none":
            return None

        try:
            if isinstance(default_value, int):
                return int(text)
            elif isinstance(default_value, float):
                return float(text)
            elif isinstance(default_value, tuple):
                values = text.strip("() ").split(",")
                return tuple(float(v.strip()) for v in values)
            elif isinstance(default_value, str):
                return text
            elif default_value is None:
                if "." in text:
                    return float(text)
                else:
                    return int(text)
            else:
                return text
        except (ValueError, TypeError):
            return default_value

    def validate_parameter(self, key, value):  # noqa: C901
        try:
            if key == "strategy":
                strategies = self.get_options_for_parameter("strategy")
                if value not in strategies:
                    return False, f"Invalid strategy. Choose from {strategies}."
            elif key == "maxiter":
                if not isinstance(value, int) or value < 1:
                    return False, "Must be an integer >= 1."
            elif key == "popsize":
                if not isinstance(value, int) or value < 1:
                    return False, "Must be an integer >= 1."
            elif key == "tol":
                if not isinstance(value, (int, float)) or value < 0:
                    return False, "Must be a non-negative number."
            elif key == "mutation":
                if isinstance(value, tuple):
                    if len(value) != 2 or not all(0 <= v <= 2 for v in value):
                        return False, "Must be a tuple of two numbers in [0, 2]."
                elif isinstance(value, (int, float)):
                    if not 0 <= value <= 2:
                        return False, "Must be in [0, 2]."
                else:
                    return False, "Invalid format."
            elif key == "recombination":
                if not isinstance(value, (int, float)) or not 0 <= value <= 1:
                    return False, "Must be in [0, 1]."
            elif key == "seed":
                if not (isinstance(value, int) or value is None):
                    return False, "Must be an integer or None."
            elif key == "atol":
                if not isinstance(value, (int, float)) or value < 0:
                    return False, "Must be a non-negative number."
            elif key == "updating":
                options = self.get_options_for_parameter("updating")
                if value not in options:
                    return False, f"Must be one of {options}."
            elif key == "workers":
                # The code currently does not support parallel processes other than 1.
                if not isinstance(value, int) or value < 1 or value > 1:
                    return False, "Must be an integer = 1. Parallel processing is not supported."
            return True, ""
        except Exception as e:
            return False, f"Error validating parameter: {str(e)}"

    def get_tooltip_for_parameter(self, param_name):
        tooltips = {
            "strategy": "The strategy for differential evolution.",
            "maxiter": "Maximum number of iterations. Must be >= 1.",
            "popsize": "Population size. Must be >= 1.",
            "tol": "Tolerance. Must be non-negative.",
            "mutation": "Mutation factor in [0, 2] or tuple of two values.",
            "recombination": "Recombination factor in [0, 1].",
            "workers": "Number of processes. Must be 1.",
        }
        return tooltips.get(param_name, "")

    def get_options_for_parameter(self, param_name):
        options = {
            "strategy": [
                "best1bin",
                "best1exp",
                "rand1exp",
                "randtobest1exp",
                "currenttobest1exp",
                "best2exp",
                "rand2exp",
                "randtobest1bin",
                "currenttobest1bin",
                "best2bin",
                "rand2bin",
                "rand1bin",
            ],
            "init": ["latinhypercube", "random"],
            "updating": ["immediate", "deferred"],
        }
        return options.get(param_name, [])


DIFFERENTIAL_EVOLUTION_DEFAULT_KWARGS = {
    "strategy": "best1bin",
    "maxiter": 1000,
    "popsize": 15,
    "tol": 0.01,
    "mutation": (0.5, 1),
    "recombination": 0.7,
    "seed": None,
    "callback": None,
    "disp": False,
    "polish": True,
    "init": "latinhypercube",
    "atol": 0,
    "updating": "deferred",
    "workers": 1,
    "constraints": (),
}
