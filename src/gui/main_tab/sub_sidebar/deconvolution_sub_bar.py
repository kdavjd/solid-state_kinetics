import json
import os
from collections import defaultdict

import numpy as np
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.core.app_settings import MODEL_FREE_DIFFERENTIAL_EVOLUTION_DEFAULT_KWARGS, OperationType
from src.core.logger_config import logger
from src.core.logger_console import LoggerConsole as console


class FileTransferButtons(QWidget):
    import_reactions_signal = pyqtSignal(dict)
    export_reactions_signal = pyqtSignal(dict)

    def __init__(self, parent=None):
        """
        Initialize the file transfer buttons widget.
        """
        super().__init__(parent)

        self.layout = QVBoxLayout(self)

        self.load_reactions_button = QPushButton("import")
        self.export_reactions_button = QPushButton("export")

        self.buttons_layout = QHBoxLayout()
        self.buttons_layout.addWidget(self.load_reactions_button)
        self.buttons_layout.addWidget(self.export_reactions_button)
        self.layout.addLayout(self.buttons_layout)

        self.load_reactions_button.clicked.connect(self.load_reactions)
        self.export_reactions_button.clicked.connect(self._export_reactions)

    def load_reactions(self):
        """
        Opens a file dialog to select a JSON file for importing reaction data.
        Emits the 'import_reactions_signal' upon success.
        """
        import_file_name, _ = QFileDialog.getOpenFileName(
            self, "Select the JSON file to import the data", "", "JSON Files (*.json)"
        )

        if import_file_name:
            self.import_reactions_signal.emit(
                {"import_file_name": import_file_name, "operation": OperationType.IMPORT_REACTIONS}
            )

    def _generate_suggested_file_name(self, file_name: str, data: dict):
        """
        Generate a suggested file name for exporting reactions based on the number and types of reactions.

        Args:
            file_name (str): Base file name.
            data (dict): Reaction data dictionary.

        Returns:
            str: Suggested file name incorporating reaction count and types.
        """
        n_reactions = len(data)
        reaction_types = []
        for reaction_key, reaction_data in data.items():
            function = reaction_data.get("function", "")
            if function == "gauss":
                reaction_types.append("gs")
            elif function == "fraser":
                reaction_types.append("fr")
            elif function == "ads":
                reaction_types.append("ads")

        reaction_codes = "_".join(reaction_types)
        base_name = os.path.splitext(os.path.basename(file_name))[0]
        suggested_file_name = f"{base_name}_{n_reactions}_rcts_{reaction_codes}.json"
        return suggested_file_name

    def _export_reactions(self):
        self.export_reactions_signal.emit(
            {"function": self._generate_suggested_file_name, "operation": OperationType.EXPORT_REACTIONS}
        )

    def export_reactions(self, data, suggested_file_name):
        """
        Export the provided reaction data to a JSON file chosen by the user.

        Args:
            data (dict): Reaction data to export.
            suggested_file_name (str): Suggested file name for saving.
        """
        save_file_name, _ = QFileDialog.getSaveFileName(
            self, "Select a location to save JSON", suggested_file_name, "JSON Files (*.json)"
        )

        if save_file_name:
            with open(save_file_name, "w", encoding="utf-8") as file:
                json.dump(data, file, ensure_ascii=False, indent=4, cls=NumpyArrayEncoder)
                console.log(f"Data successfully exported to file:\n\n{save_file_name}")
                logger.info(f"Data successfully exported to file: {save_file_name}")


class NumpyArrayEncoder(json.JSONEncoder):
    """
    Custom JSON encoder that converts NumPy arrays to lists for JSON serialization.
    """

    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super(NumpyArrayEncoder, self).default(obj)


class ReactionTable(QWidget):
    reaction_added = pyqtSignal(dict)
    reaction_removed = pyqtSignal(dict)
    reaction_chosed = pyqtSignal(dict)
    reaction_function_changed = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)

        self.add_reaction_button = QPushButton("add reaction")
        self.del_reaction_button = QPushButton("delete")

        self.top_buttons_layout = QHBoxLayout()
        self.top_buttons_layout.addWidget(self.add_reaction_button)
        self.top_buttons_layout.addWidget(self.del_reaction_button)
        self.layout.addLayout(self.top_buttons_layout)

        self.reactions_tables = {}
        self.reactions_counters = defaultdict(int)
        self.active_file = None
        self.active_reaction = ""
        self.calculation_settings = defaultdict(dict)
        self.deconvolution_settings = defaultdict(dict)

        self.settings_button = QPushButton("settings")
        self.layout.addWidget(self.settings_button)

        self.add_reaction_button.clicked.connect(self.add_reaction)
        self.del_reaction_button.clicked.connect(self.del_reaction)
        self.settings_button.clicked.connect(self.open_settings)

    def switch_file(self, file_name):
        """
        Switch the active file's reaction table to the specified file_name.
        Create a new table if none exists for that file.
        """
        if file_name not in self.reactions_tables:
            self.reactions_tables[file_name] = QTableWidget()
            self.reactions_tables[file_name].setColumnCount(2)
            self.reactions_tables[file_name].setHorizontalHeaderLabels(["name", "function"])
            self.reactions_tables[file_name].horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            self.reactions_tables[file_name].itemClicked.connect(self.selected_reaction)
            self.layout.addWidget(self.reactions_tables[file_name])

        if self.active_file:
            self.reactions_tables[self.active_file].setVisible(False)

        self.reactions_tables[file_name].setVisible(True)
        self.active_file = file_name

    def function_changed(self, reaction_name, combo):
        """
        Handle changes in the reaction function.

        Args:
            reaction_name (str): Name of the reaction.
            combo (QComboBox): ComboBox widget for selecting the function.
        """
        function = combo.currentText()
        data_change = {
            "path_keys": [reaction_name, "function"],
            "operation": OperationType.UPDATE_VALUE,
            "value": function,
        }
        self.reaction_function_changed.emit(data_change)
        logger.debug(f"Reaction changed for {reaction_name}: {function}")

    def add_reaction(self, checked=False, reaction_name=None, function_name=None, emit_signal=True):
        """
        Add a new reaction to the currently active file's table.
        If no file is active, show a warning message.

        Args:
            checked (bool): Unused checkbox state for signal/slot compatibility.
            reaction_name (str): Custom reaction name. If None, a default name is generated.
            function_name (str): Initial function name for the reaction. If None, 'gauss' is used.
            emit_signal (bool): Whether to emit the 'reaction_added' signal.
        """
        if not self.active_file:
            QMessageBox.warning(self, "The file is not selected", "Choose an experiment")
            return

        table = self.reactions_tables[self.active_file]
        row_count = table.rowCount()
        table.insertRow(row_count)

        if reaction_name is None:
            reaction_name = f"reaction_{self.reactions_counters[self.active_file]}"
        else:
            # Validate the reaction name format
            try:
                counter_value = int(reaction_name.split("_")[-1])
                self.reactions_counters[self.active_file] = max(
                    self.reactions_counters[self.active_file], counter_value + 1
                )
            except ValueError:
                logger.error(f"Invalid reaction name format: {reaction_name}")

        combo = QComboBox()
        combo.addItems(["gauss", "fraser", "ads"])
        if function_name:
            combo.setCurrentText(function_name)
        else:
            combo.setCurrentText("gauss")
        combo.currentIndexChanged.connect(lambda: self.function_changed(reaction_name, combo))

        table.setItem(row_count, 0, QTableWidgetItem(reaction_name))
        table.setCellWidget(row_count, 1, combo)

        if emit_signal:
            reaction_data = {"path_keys": [reaction_name], "operation": OperationType.ADD_REACTION}
            self.reaction_added.emit(reaction_data)

        self.reactions_counters[self.active_file] += 1

    def on_fail_add_reaction(self):
        """
        Roll back the last added reaction if addition failed.
        """
        if not self.active_file:
            logger.debug("No file selected. Cannot roll back last addition.")
            return

        table = self.reactions_tables[self.active_file]
        if table.rowCount() > 0:
            last_row = table.rowCount() - 1
            table.removeRow(last_row)
            self.reactions_counters[self.active_file] -= 1
            logger.debug("Failed to add reaction. The last row has been removed.")

    def del_reaction(self):
        """
        Delete the last reaction from the currently active file's table.
        If no file is active or no reactions are available, show a warning.
        """
        if not self.active_file:
            QMessageBox.warning(self, "The file is not selected.", "Choose an experiment")
            return

        table = self.reactions_tables[self.active_file]
        if table.rowCount() > 0:
            last_row = table.rowCount() - 1
            item = table.item(last_row, 0)
            if item is not None:
                reaction_name = item.text()
                table.removeRow(last_row)
                self.reactions_counters[self.active_file] -= 1

                reaction_data = {
                    "path_keys": [reaction_name],
                    "operation": OperationType.REMOVE_REACTION,
                }
                self.reaction_removed.emit(reaction_data)
            else:
                logger.debug("Attempted to delete an empty cell.")
        else:
            QMessageBox.warning(self, "Empty list", "There are no reactions to delete.")

    def selected_reaction(self, item):
        """
        Handle selection of a reaction from the table.
        Emits 'reaction_chosed' signal.

        Args:
            item (QTableWidgetItem): The selected table item.
        """
        row = item.row()
        reaction_name = self.reactions_tables[self.active_file].item(row, 0).text()
        self.active_reaction = reaction_name
        logger.debug(f"Active reaction: {reaction_name}")
        self.reaction_chosed.emit({"path_keys": [reaction_name], "operation": OperationType.HIGHLIGHT_REACTION})

    def open_settings(self):
        """
        Open a dialog to configure calculation and deconvolution settings for the current file's reactions.
        """
        if self.active_file:
            table = self.reactions_tables[self.active_file]
            reactions = {}
            for row in range(table.rowCount()):
                reaction_name = table.item(row, 0).text()
                combo = table.cellWidget(row, 1)
                reactions[reaction_name] = combo

            initial_settings = self.calculation_settings[self.active_file]
            initial_deconvolution_settings = self.deconvolution_settings.get(self.active_file, {})
            dialog = CalculationSettingsDialog(reactions, initial_settings, initial_deconvolution_settings, self)
            if dialog.exec():
                selected_functions, selected_method, deconvolution_parameters = dialog.get_selected_functions()

                # Validate that each reaction has at least one function selected
                empty_keys = [key for key, value in selected_functions.items() if not value]
                if empty_keys:
                    QMessageBox.warning(
                        self,
                        "unselected functions",
                        f"{', '.join(empty_keys)} must be described by at least one function.",
                    )
                    self.open_settings()
                    return

                self.calculation_settings[self.active_file] = selected_functions
                self.deconvolution_settings[self.active_file] = {
                    "method": selected_method,
                    "method_parameters": deconvolution_parameters,
                }
                logger.info(f"Selected functions: {selected_functions}")
                logger.info(f"Deconvolution settings: {self.deconvolution_settings[self.active_file]}")

                formatted_functions = "\n".join([f"{key}: {value}" for key, value in selected_functions.items()])
                message = f"    {self.active_file}\n{formatted_functions}"

                QMessageBox.information(self, "calculation settings", f"updated for:\n{message}")
        else:
            QMessageBox.warning(self, "File is not selected.", "Choose an experiment")


class CalculationSettingsDialog(QDialog):
    def __init__(self, reactions, initial_settings, initial_deconvolution_settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("calculation settings")
        self.reactions = reactions
        self.initial_settings = initial_settings
        self.initial_deconvolution_settings = initial_deconvolution_settings
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        reactions_group_box = QGroupBox("functions")
        reactions_layout = QGridLayout()
        reactions_group_box.setLayout(reactions_layout)
        self.checkboxes = {}
        row = 0
        for reaction_name, combo in self.reactions.items():
            functions = [combo.itemText(i) for i in range(combo.count())]
            self.checkboxes[reaction_name] = []
            col = 0
            reaction_label = QLabel(reaction_name)
            reactions_layout.addWidget(reaction_label, row, col)
            col += 1
            for function in functions:
                checkbox = QCheckBox(function)
                checkbox.setChecked(function in self.initial_settings.get(reaction_name, []))
                self.checkboxes[reaction_name].append(checkbox)
                reactions_layout.addWidget(checkbox, row, col)
                col += 1
            row += 1

        main_layout.addWidget(reactions_group_box)

        deconvolution_group_box = QGroupBox("deconvolution parameters")
        deconvolution_layout = QVBoxLayout()
        deconvolution_group_box.setLayout(deconvolution_layout)

        method_layout = QHBoxLayout()
        method_label = QLabel("deconvolution method:")
        self.deconvolution_method_combo = QComboBox()
        self.deconvolution_method_combo.addItems(["differential_evolution", "another_method"])
        method_layout.addWidget(method_label)
        method_layout.addWidget(self.deconvolution_method_combo)
        deconvolution_layout.addLayout(method_layout)

        self.method_parameters_layout = QGridLayout()
        deconvolution_layout.addLayout(self.method_parameters_layout)

        main_layout.addWidget(deconvolution_group_box)

        if self.initial_deconvolution_settings:
            initial_method = self.initial_deconvolution_settings.get("method", "differential_evolution")
            index = self.deconvolution_method_combo.findText(initial_method)
            if index >= 0:
                self.deconvolution_method_combo.setCurrentIndex(index)
        else:
            self.deconvolution_method_combo.setCurrentText("differential_evolution")

        self.update_method_parameters()
        self.deconvolution_method_combo.currentIndexChanged.connect(self.update_method_parameters)

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)

    def update_method_parameters(self):
        """
        Update the displayed parameters for the selected deconvolution method.
        Clears previous parameters and populates the layout with fields for the current method.
        """
        while self.method_parameters_layout.count():
            item = self.method_parameters_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        selected_method = self.deconvolution_method_combo.currentText()
        if selected_method == "differential_evolution":
            self.de_parameters = {}
            initial_params = {}
            if (
                self.initial_deconvolution_settings
                and self.initial_deconvolution_settings.get("method") == selected_method
            ):
                initial_params = self.initial_deconvolution_settings.get("deconvolution_parameters", {})
            row = 0
            for key, value in MODEL_FREE_DIFFERENTIAL_EVOLUTION_DEFAULT_KWARGS.items():
                label = QLabel(key)
                tooltip = self.get_tooltip_for_parameter(key)
                label.setToolTip(tooltip)
                # Choosing widget type based on parameter type
                if isinstance(value, bool):
                    field = QCheckBox()
                    field.setChecked(initial_params.get(key, value))
                    field.setToolTip(tooltip)
                elif key in ["strategy", "init", "updating"]:
                    field = QComboBox()
                    options = self.get_options_for_parameter(key)
                    field.addItems(options)
                    field.setCurrentText(initial_params.get(key, value))
                    field.setToolTip(tooltip)
                else:
                    field = QLineEdit(str(initial_params.get(key, value)))
                    field.setToolTip(tooltip)
                self.de_parameters[key] = field
                self.method_parameters_layout.addWidget(label, row, 0)
                self.method_parameters_layout.addWidget(field, row, 1)
                row += 1
        elif selected_method == "another_method":
            # No parameters defined for this method in this example.
            pass

    def get_tooltip_for_parameter(self, param_name):
        tooltips = {
            "strategy": "The strategy for differential evolution. Choose one of the available options.",
            "maxiter": "Maximum number of iterations. An integer >= 1.",
            "popsize": "Population size. An integer >= 1.",
            "tol": "Relative tolerance for stop criteria. A non-negative number.",
            "mutation": "Mutation factor. A number or tuple of two numbers in [0, 2].",
            "recombination": "Recombination factor in [0, 1].",
            "seed": "Random seed. An integer or None.",
            "callback": "Callback function. Leave empty if not required.",
            "disp": "Display status during optimization.",
            "polish": "Perform a final polish optimization after differential evolution is done.",
            "init": "Population initialization method.",
            "atol": "Absolute tolerance for stop criteria. A non-negative number.",
            "updating": "Population updating mode: immediate or deferred.",
            "workers": "Number of processes for parallel computing. Must be 1 here.",
            "constraints": "Constraints for the optimization. Leave empty if not required.",
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

    def get_selected_functions(self):
        """
        Get the selected functions for each reaction and the chosen deconvolution method and parameters.

        Returns:
            tuple: (selected_functions (dict), selected_method (str), deconvolution_parameters (dict))
        """
        selected_functions = {}
        for reaction_name, checkboxes in self.checkboxes.items():
            selected_functions[reaction_name] = [cb.text() for cb in checkboxes if cb.isChecked()]
        selected_method, deconvolution_parameters = self.get_deconvolution_parameters()
        return selected_functions, selected_method, deconvolution_parameters

    def get_deconvolution_parameters(self):
        """
        Validate and retrieve deconvolution parameters for the selected method.

        Returns:
            tuple: (selected_method (str), parameters (dict))
        """
        selected_method = self.deconvolution_method_combo.currentText()
        parameters = {}
        errors = []
        if selected_method == "differential_evolution":
            for key, field in self.de_parameters.items():
                if isinstance(field, QCheckBox):
                    parameters[key] = field.isChecked()
                elif isinstance(field, QComboBox):
                    parameters[key] = field.currentText()
                else:
                    text = field.text()
                    default_value = MODEL_FREE_DIFFERENTIAL_EVOLUTION_DEFAULT_KWARGS[key]
                    value = self.convert_to_type(text, default_value)

                    is_valid, error_msg = self.validate_parameter(key, value)
                    if not is_valid:
                        errors.append(f"Parameter '{key}': {error_msg}")
                    parameters[key] = value
            if errors:
                error_message = "\n".join(errors)
                QMessageBox.warning(self, "Error entering parameters", error_message)
                return None, None
        elif selected_method == "another_method":
            parameters = {}
        return selected_method, parameters

    def convert_to_type(self, text, default_value):
        """
        Convert text input into the appropriate type based on the default value type.

        Args:
            text (str): The string to convert.
            default_value: The default value to infer type.

        Returns:
            Converted value or the default value if conversion fails.
        """
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
                if text == "" or text.lower() == "none":
                    return None
                else:
                    return text
            else:
                return text
        except ValueError:
            return default_value

    def validate_parameter(self, key, value):  # noqa: C901
        """
        Validate a parameter's value according to differential evolution rules.

        Args:
            key (str): Parameter name.
            value: Parameter value.

        Returns:
            tuple(bool, str): (Is valid, Error message if not valid)
        """
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

    def accept(self):
        """
        Validate settings before closing the dialog.
        Ensures each reaction has at least one function selected and parameters are valid.
        """
        selected_functions = {}
        for reaction_name, checkboxes in self.checkboxes.items():
            selected = [cb.text() for cb in checkboxes if cb.isChecked()]
            if not selected:
                QMessageBox.warning(
                    self, "Settings error", f"raction '{reaction_name}' must have at least one function."
                )
                return
            selected_functions[reaction_name] = selected

        selected_method, deconvolution_parameters = self.get_deconvolution_parameters()
        if deconvolution_parameters is None:
            # Error in parameters, do not close the dialog
            return
        self.selected_functions = selected_functions
        self.selected_method = selected_method
        self.deconvolution_parameters = deconvolution_parameters
        super().accept()

    def get_results(self):
        """
        Get the results selected in the dialog.

        Returns:
            tuple: (selected_functions (dict), selected_method (str), deconvolution_parameters (dict))
        """
        return self.selected_functions, self.selected_method, self.deconvolution_parameters


class CoeffsTable(QTableWidget):
    update_value = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(5, 2, parent)
        self.header_labels = ["from", "to"]
        self.row_labels_dict = {
            "gauss": ["h", "z", "w"],
            "fraser": ["h", "z", "w", "fr"],
            "ads": ["h", "z", "w", "ads1", "ads2"],
        }
        self.default_row_labels = ["h", "z", "w", "_", "_"]
        self.setHorizontalHeaderLabels(self.header_labels)
        self.setVerticalHeaderLabels(self.default_row_labels)
        self.mock_table()
        self.calculate_fixed_height()
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.cellChanged.connect(self.update_reaction_params)
        self._is_table_filling = False

    def calculate_fixed_height(self):
        """
        Adjust the table's height based on the number of rows and header heights.
        """
        row_height = self.rowHeight(0)
        borders_height = len(self.default_row_labels) * 2
        header_height = self.horizontalHeader().height()
        total_height = (row_height * len(self.default_row_labels)) + header_height + borders_height
        self.setFixedHeight(total_height)

    def mock_table(self):
        """
        Fill the table with 'NaN' as placeholder values.
        """
        for i in range(len(self.default_row_labels)):
            for j in range(len(self.header_labels)):
                self.setItem(i, j, QTableWidgetItem("NaN"))

    def fill_table(self, reaction_params: dict):
        """
        Fill the table with given reaction parameters.

        Args:
            reaction_params (dict): Dictionary containing 'lower_bound_coeffs' and 'upper_bound_coeffs',
                                    each a list with indices [2] for parameter data.
        """
        logger.debug(f"Received reaction parameters for the table: {reaction_params}")
        param_keys = ["lower_bound_coeffs", "upper_bound_coeffs"]
        function_type = reaction_params[param_keys[0]][1]
        if function_type not in self.row_labels_dict:
            logger.error(f"Unknown function type: {function_type}")
            return

        self._is_table_filling = True
        row_labels = self.row_labels_dict[function_type]
        self.setRowCount(len(row_labels))
        self.setVerticalHeaderLabels(row_labels)

        for j, key in enumerate(param_keys):
            try:
                # data structure: [x_range, function_type, params]
                data = reaction_params[key][2]
                for i in range(min(len(row_labels), len(data))):
                    value = f"{data[i]:.2f}"
                    self.setItem(i, j, QTableWidgetItem(value))
            except IndexError as e:
                logger.error(f"Index error processing data '{key}': {e}")

        self.mock_remaining_cells(len(row_labels))
        self._is_table_filling = False

    def mock_remaining_cells(self, num_rows):
        """
        Fill remaining cells below the actual data with 'NaN'.
        This ensures a consistent table size if needed.
        """
        for i in range(num_rows, len(self.default_row_labels)):
            for j in range(len(self.header_labels)):
                self.setItem(i, j, QTableWidgetItem("NaN"))

    def update_reaction_params(self, row, column):
        """
        Handle updates to the reaction parameter cell values.
        Emits 'update_value' signal with the changed data.

        Args:
            row (int): Row index of the changed cell.
            column (int): Column index of the changed cell.
        """
        if not self._is_table_filling:
            try:
                item = self.item(row, column)
                value = float(item.text())
                row_label = self.verticalHeaderItem(row).text()
                column_label = self.horizontalHeaderItem(column).text()

                path_keys = [self.column_to_bound(column_label), row_label]
                data_change = {
                    "path_keys": path_keys,
                    "operation": OperationType.UPDATE_VALUE,
                    "value": value,
                }
                self.update_value.emit(data_change)
            except ValueError as e:
                console.log(f"Invalid data for conversion to number: row {row+1}, column {column+1}")
                logger.error(f"Invalid data for conversion to number: row {row}, column {column}: {e}")

    def column_to_bound(self, column_label):
        return {"from": "lower_bound_coeffs", "to": "upper_bound_coeffs"}.get(column_label, "")


class CalcButtons(QWidget):
    calculation_started = pyqtSignal(dict)
    calculation_stopped = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.start_button = QPushButton("calculate")
        self.stop_button = QPushButton("stop calculating")
        self.layout.addWidget(self.start_button)

        self.start_button.clicked.connect(self.check_and_start_calculation)
        self.stop_button.clicked.connect(self.stop_calculation)
        self.is_calculating = False
        self.parent = parent

    def revert_to_default(self):
        if self.is_calculating:
            self.is_calculating = False
            self.layout.replaceWidget(self.stop_button, self.start_button)
            self.stop_button.hide()
            self.start_button.show()

    def check_and_start_calculation(self):
        """
        Check that a file is active and settings are chosen before starting the calculation.
        If settings are missing, prompt the user to configure them.
        """
        if not self.parent.reactions_table.active_file:
            QMessageBox.warning(self, "The file is not selected.", "Choose an experiment")
            return

        settings = self.parent.reactions_table.calculation_settings.get(self.parent.reactions_table.active_file, {})
        deconvolution_settings = self.parent.reactions_table.deconvolution_settings.get(
            self.parent.reactions_table.active_file, {}
        )
        if not settings or not deconvolution_settings:
            QMessageBox.information(self, "Settings are required.", "The calculation settings are not set.")
            self.parent.open_settings_dialog()
        else:
            data = {
                "path_keys": [],
                "operation": OperationType.DECONVOLUTION,
                "chosen_functions": settings,
                "deconvolution_settings": deconvolution_settings,
            }
            self.calculation_started.emit(data)
            self.start_calculation()

    def start_calculation(self):
        """
        Switch to 'stop' mode indicating that the calculation is in progress.
        """
        self.is_calculating = True
        self.layout.replaceWidget(self.start_button, self.stop_button)
        self.start_button.hide()
        self.stop_button.show()

    def stop_calculation(self):
        if self.is_calculating:
            self.calculation_stopped.emit({"operation": OperationType.STOP_CALCULATION})
            self.is_calculating = False
            self.layout.replaceWidget(self.stop_button, self.start_button)
            self.stop_button.hide()
            self.start_button.show()


class DeconvolutionSubBar(QWidget):
    update_value = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        self.reactions_table = ReactionTable(self)
        self.coeffs_table = CoeffsTable(self)
        self.file_transfer_buttons = FileTransferButtons(self)
        self.calc_buttons = CalcButtons(self)

        layout.addWidget(self.reactions_table)
        layout.addWidget(self.coeffs_table)
        layout.addWidget(self.file_transfer_buttons)
        layout.addWidget(self.calc_buttons)

        self.coeffs_table.update_value.connect(self.handle_update_value)
        self.reactions_table.reaction_function_changed.connect(self.handle_update_function_value)

    def handle_update_value(self, data: dict):
        """
        Handle updates to reaction parameter values by inserting the active reaction into path_keys,
        then emitting the 'update_value' signal.

        Args:
            data (dict): Update data containing path_keys and new value.
        """
        if self.reactions_table.active_reaction:
            data["path_keys"].insert(0, self.reactions_table.active_reaction)
            self.update_value.emit(data)
        else:
            console.log("Select a reaction before changing its values.")

    def handle_update_function_value(self, data: dict):
        """
        Handle updates to a reaction's function.

        Args:
            data (dict): Data for updating the reaction function.
        """
        if self.reactions_table.active_reaction is not None:
            self.update_value.emit(data)

    def open_settings_dialog(self):
        """
        Opens the calculation settings dialog via the ReactionTable instance.
        """
        self.reactions_table.open_settings()

    def get_reactions_for_file(self, file_name):
        """
        Retrieve a dictionary of reaction names and their associated ComboBoxes for a given file.

        Args:
            file_name (str): The name of the file.

        Returns:
            dict: Mapping of reaction_name -> QComboBox for reactions in the file.
        """
        table = self.reactions_table.reactions_tables[file_name]
        reactions = {}
        for row in range(table.rowCount()):
            reaction_name = table.item(row, 0).text()
            combo = table.cellWidget(row, 1)
            reactions[reaction_name] = combo
        return reactions
