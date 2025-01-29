from PyQt6.QtCore import pyqtSignal, pyqtSlot
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
        settings_button = QPushButton("Settings")
        start_button = QPushButton("Start")
        buttons_layout.addWidget(settings_button)
        buttons_layout.addWidget(start_button)

        self.models_scene = ModelsScheme(self)
        bottom_layout.addLayout(buttons_layout)
        bottom_layout.addWidget(self.models_scene)
        main_layout.addLayout(bottom_layout)

        start_button.clicked.connect(self.start_simulation)

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

    # def open_settings(self):
    #     # Составляем словарь с реакциями и привязанными к ним QComboBox'ами (или другими виджетами)
    #     reactions = {}
    #     ...

    #     # Создаём и показываем диалог
    #     dialog = CalculationSettingsDialog(
    #         reactions,
    #         self
    #     )
    #     if dialog.exec():
    #         selected_functions, selected_method, deconvolution_parameters = dialog.get_selected_functions()

    #         # Проверяем, что для каждой реакции выбрана хотя бы одна функция
    #         empty_keys = [key for key, value in selected_functions.items() if not value]
    #         if empty_keys:
    #             QMessageBox.warning(
    #                 self,
    #                 "unselected functions",
    #                 f"{', '.join(empty_keys)} must be described by at least one function.",
    #             )
    #             # Если какие-то реакции остались без функций, заново откроем настройки
    #             self.open_settings()
    #             return

    #         # Сохраняем выбранные пользователем настройки
    #         self.calculation_settings[self.active_file] = selected_functions
    #         self.deconvolution_settings[self.active_file] = {
    #             "method": selected_method,
    #             "method_parameters": deconvolution_parameters,
    #         }

    #         # При желании можно добавить вывод в лог:
    #         # logger.info(f"Selected functions: {selected_functions}")
    #         # logger.info(f"Deconvolution settings: {self.deconvolution_settings[self.active_file]}")

    #         # И уведомим пользователя
    #         formatted_functions = "\n".join([f"{key}: {value}" for key, value in selected_functions.items()])
    #         message = f"    {self.active_file}\n{formatted_functions}"

    #         QMessageBox.information(self, "calculation settings", f"updated for:\n{message}")


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


# class CalculationSettingsDialog(QDialog):
#     def __init__(self, reactions, initial_settings, initial_deconvolution_settings, parent=None):
#         super().__init__(parent)
#         self.setWindowTitle("Calculation Settings")

#         self.reactions = reactions or []  # На случай, если передадут None
#         # self.initial_settings = initial_settings
#         # self.initial_deconvolution_settings = initial_deconvolution_settings

#         self.init_ui()

#     def init_ui(self):
#         main_layout = QVBoxLayout()
#         self.setLayout(main_layout)

#         headers = [
#             "Reaction Type",
#             "Ea_min",
#             "Ea_max",
#             "log_A_min",
#             "log_A_max",
#             "contrib_min",
#             "contrib_max",
#         ]
#         table = QTableWidget(len(self.reactions), len(headers))
#         table.setHorizontalHeaderLabels(headers)

#         table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

#         default_ea_min, default_ea_max = 1000, 2000000
#         default_logA_min, default_logA_max = 0.1, 100
#         default_contrib_min, default_contrib_max = 0.01, 1.0

#         for row_index, reaction in enumerate(self.reactions):
#             r_type = reaction.get("reaction_type", "F1")

#             ea_min = reaction.get("Ea_min", default_ea_min)
#             ea_max = reaction.get("Ea_max", default_ea_max)
#             log_a_min = reaction.get("log_A_min", default_logA_min)
#             log_a_max = reaction.get("log_A_max", default_logA_max)
#             contrib_min = reaction.get("contribution_min", default_contrib_min)
#             contrib_max = reaction.get("contribution_max", default_contrib_max)

#             # Добавляем ячейки в таблицу
#             table.setItem(row_index, 0, QTableWidgetItem(str(r_type)))
#             table.setItem(row_index, 1, QTableWidgetItem(str(ea_min)))
#             table.setItem(row_index, 2, QTableWidgetItem(str(ea_max)))
#             table.setItem(row_index, 3, QTableWidgetItem(str(log_a_min)))
#             table.setItem(row_index, 4, QTableWidgetItem(str(log_a_max)))
#             table.setItem(row_index, 5, QTableWidgetItem(str(contrib_min)))
#             table.setItem(row_index, 6, QTableWidgetItem(str(contrib_max)))

#         main_layout.addWidget(table)

#         # Кнопки OK/Cancel - при необходимости
#         button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
#         button_box.accepted.connect(self.accept)
#         button_box.rejected.connect(self.reject)
#         main_layout.addWidget(button_box)

#     def update_method_parameters(self):
#         """
#         Update the displayed parameters for the selected deconvolution method.
#         Clears previous parameters and populates the layout with fields for the current method.
#         """
#         while self.method_parameters_layout.count():
#             item = self.method_parameters_layout.takeAt(0)
#             widget = item.widget()
#             if widget is not None:
#                 widget.deleteLater()
#         selected_method = self.deconvolution_method_combo.currentText()
#         if selected_method == "differential_evolution":
#             self.de_parameters = {}
#             initial_params = {}
#             if (
#                 self.initial_deconvolution_settings
#                 and self.initial_deconvolution_settings.get("method") == selected_method
#             ):
#                 initial_params = self.initial_deconvolution_settings.get("deconvolution_parameters", {})
#             row = 0
#             for key, value in DIFFERENTIAL_EVOLUTION_DEFAULT_KWARGS.items():
#                 label = QLabel(key)
#                 tooltip = self.get_tooltip_for_parameter(key)
#                 label.setToolTip(tooltip)
#                 # Choosing widget type based on parameter type
#                 if isinstance(value, bool):
#                     field = QCheckBox()
#                     field.setChecked(initial_params.get(key, value))
#                     field.setToolTip(tooltip)
#                 elif key in ["strategy", "init", "updating"]:
#                     field = QComboBox()
#                     options = self.get_options_for_parameter(key)
#                     field.addItems(options)
#                     field.setCurrentText(initial_params.get(key, value))
#                     field.setToolTip(tooltip)
#                 else:
#                     field = QLineEdit(str(initial_params.get(key, value)))
#                     field.setToolTip(tooltip)
#                 self.de_parameters[key] = field
#                 self.method_parameters_layout.addWidget(label, row, 0)
#                 self.method_parameters_layout.addWidget(field, row, 1)
#                 row += 1
#         elif selected_method == "another_method":
#             # No parameters defined for this method in this example.
#             pass

#     def get_tooltip_for_parameter(self, param_name):
#         tooltips = {
#             "strategy": "The strategy for differential evolution. Choose one of the available options.",
#             "maxiter": "Maximum number of iterations. An integer >= 1.",
#             "popsize": "Population size. An integer >= 1.",
#             "tol": "Relative tolerance for stop criteria. A non-negative number.",
#             "mutation": "Mutation factor. A number or tuple of two numbers in [0, 2].",
#             "recombination": "Recombination factor in [0, 1].",
#             "seed": "Random seed. An integer or None.",
#             "callback": "Callback function. Leave empty if not required.",
#             "disp": "Display status during optimization.",
#             "polish": "Perform a final polish optimization after differential evolution is done.",
#             "init": "Population initialization method.",
#             "atol": "Absolute tolerance for stop criteria. A non-negative number.",
#             "updating": "Population updating mode: immediate or deferred.",
#             "workers": "Number of processes for parallel computing. Must be 1 here.",
#             "constraints": "Constraints for the optimization. Leave empty if not required.",
#         }
#         return tooltips.get(param_name, "")

#     def get_options_for_parameter(self, param_name):
#         options = {
#             "strategy": [
#                 "best1bin",
#                 "best1exp",
#                 "rand1exp",
#                 "randtobest1exp",
#                 "currenttobest1exp",
#                 "best2exp",
#                 "rand2exp",
#                 "randtobest1bin",
#                 "currenttobest1bin",
#                 "best2bin",
#                 "rand2bin",
#                 "rand1bin",
#             ],
#             "init": ["latinhypercube", "random"],
#             "updating": ["immediate", "deferred"],
#         }
#         return options.get(param_name, [])

#     def get_selected_functions(self):
#         """
#         Get the selected functions for each reaction and the chosen deconvolution method and parameters.

#         Returns:
#             tuple: (selected_functions (dict), selected_method (str), deconvolution_parameters (dict))
#         """
#         selected_functions = {}
#         for reaction_name, checkboxes in self.checkboxes.items():
#             selected_functions[reaction_name] = [cb.text() for cb in checkboxes if cb.isChecked()]
#         selected_method, deconvolution_parameters = self.get_deconvolution_parameters()
#         return selected_functions, selected_method, deconvolution_parameters

#     def get_deconvolution_parameters(self):
#         """
#         Validate and retrieve deconvolution parameters for the selected method.

#         Returns:
#             tuple: (selected_method (str), parameters (dict))
#         """
#         selected_method = self.deconvolution_method_combo.currentText()
#         parameters = {}
#         errors = []
#         if selected_method == "differential_evolution":
#             for key, field in self.de_parameters.items():
#                 if isinstance(field, QCheckBox):
#                     parameters[key] = field.isChecked()
#                 elif isinstance(field, QComboBox):
#                     parameters[key] = field.currentText()
#                 else:
#                     text = field.text()
#                     default_value = DIFFERENTIAL_EVOLUTION_DEFAULT_KWARGS[key]
#                     value = self.convert_to_type(text, default_value)

#                     is_valid, error_msg = self.validate_parameter(key, value)
#                     if not is_valid:
#                         errors.append(f"Parameter '{key}': {error_msg}")
#                     parameters[key] = value
#             if errors:
#                 error_message = "\n".join(errors)
#                 QMessageBox.warning(self, "Error entering parameters", error_message)
#                 return None, None
#         elif selected_method == "another_method":
#             parameters = {}
#         return selected_method, parameters

#     def convert_to_type(self, text, default_value):
#         """
#         Convert text input into the appropriate type based on the default value type.

#         Args:
#             text (str): The string to convert.
#             default_value: The default value to infer type.

#         Returns:
#             Converted value or the default value if conversion fails.
#         """
#         try:
#             if isinstance(default_value, int):
#                 return int(text)
#             elif isinstance(default_value, float):
#                 return float(text)
#             elif isinstance(default_value, tuple):
#                 values = text.strip("() ").split(",")
#                 return tuple(float(v.strip()) for v in values)
#             elif isinstance(default_value, str):
#                 return text
#             elif default_value is None:
#                 if text == "" or text.lower() == "none":
#                     return None
#                 else:
#                     return text
#             else:
#                 return text
#         except ValueError:
#             return default_value

#     def validate_parameter(self, key, value):
#         """
#         Validate a parameter's value according to differential evolution rules.

#         Args:
#             key (str): Parameter name.
#             value: Parameter value.

#         Returns:
#             tuple(bool, str): (Is valid, Error message if not valid)
#         """
#         try:
#             if key == "strategy":
#                 strategies = self.get_options_for_parameter("strategy")
#                 if value not in strategies:
#                     return False, f"Invalid strategy. Choose from {strategies}."
#             elif key == "maxiter":
#                 if not isinstance(value, int) or value < 1:
#                     return False, "Must be an integer >= 1."
#             elif key == "popsize":
#                 if not isinstance(value, int) or value < 1:
#                     return False, "Must be an integer >= 1."
#             elif key == "tol":
#                 if not isinstance(value, (int, float)) or value < 0:
#                     return False, "Must be a non-negative number."
#             elif key == "mutation":
#                 if isinstance(value, tuple):
#                     if len(value) != 2 or not all(0 <= v <= 2 for v in value):
#                         return False, "Must be a tuple of two numbers in [0, 2]."
#                 elif isinstance(value, (int, float)):
#                     if not 0 <= value <= 2:
#                         return False, "Must be in [0, 2]."
#                 else:
#                     return False, "Invalid format."
#             elif key == "recombination":
#                 if not isinstance(value, (int, float)) or not 0 <= value <= 1:
#                     return False, "Must be in [0, 1]."
#             elif key == "seed":
#                 if not (isinstance(value, int) or value is None):
#                     return False, "Must be an integer or None."
#             elif key == "atol":
#                 if not isinstance(value, (int, float)) or value < 0:
#                     return False, "Must be a non-negative number."
#             elif key == "updating":
#                 options = self.get_options_for_parameter("updating")
#                 if value not in options:
#                     return False, f"Must be one of {options}."
#             elif key == "workers":
#                 # The code currently does not support parallel processes other than 1.
#                 if not isinstance(value, int) or value < 1 or value > 1:
#                     return False, "Must be an integer = 1. Parallel processing is not supported."
#             return True, ""
#         except Exception as e:
#             return False, f"Error validating parameter: {str(e)}"

#     def accept(self):
#         """
#         Validate settings before closing the dialog.
#         Ensures each reaction has at least one function selected and parameters are valid.
#         """
#         selected_functions = {}
#         for reaction_name, checkboxes in self.checkboxes.items():
#             selected = [cb.text() for cb in checkboxes if cb.isChecked()]
#             if not selected:
#                 QMessageBox.warning(
#                     self, "Settings error", f"raction '{reaction_name}' must have at least one function."
#                 )
#                 return
#             selected_functions[reaction_name] = selected

#         selected_method, deconvolution_parameters = self.get_deconvolution_parameters()
#         if deconvolution_parameters is None:
#             # Error in parameters, do not close the dialog
#             return
#         self.selected_functions = selected_functions
#         self.selected_method = selected_method
#         self.deconvolution_parameters = deconvolution_parameters
#         super().accept()

#     def get_results(self):
#         """
#         Get the results selected in the dialog.

#         Returns:
#             tuple: (selected_functions (dict), selected_method (str), deconvolution_parameters (dict))
#         """
#         return self.selected_functions, self.selected_method, self.deconvolution_parameters

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
