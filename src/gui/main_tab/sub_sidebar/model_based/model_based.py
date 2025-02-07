from dataclasses import dataclass

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
    QSizePolicy,
    QSlider,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.core.app_settings import NUC_MODELS_LIST, OperationType
from src.gui.main_tab.sub_sidebar.model_based.models_scheme import ModelsScheme


@dataclass
class ReactionDefaults:
    Ea_default: float = 120
    log_A_default: float = 8
    contribution_default: float = 0.5
    Ea_range: tuple = (1, 2000)
    log_A_range: tuple = (0.1, 100)
    contribution_range: tuple = (0.01, 1)


@dataclass
class AdjustmentDefaults:
    BUTTON_SIZE: int = 24
    SLIDER_MIN: int = -5
    SLIDER_MAX: int = 5
    SLIDER_TICK_INTERVAL: int = 1


@dataclass
class ReactionAdjustmentParameters:
    ea_default: float = 120
    log_a_default: float = 8
    contribution_default: float = 0.5
    ea_button_step: float = 10
    log_a_button_step: float = 1
    contribution_button_step: float = 0.1
    ea_slider_scale: float = 1
    log_a_slider_scale: float = 0.1
    contribution_slider_scale: float = 0.01


@dataclass
class LayoutSettings:
    reaction_table_column_widths: tuple[int, int, int, int] = (70, 50, 50, 50)
    reaction_table_row_heights: tuple[int, int, int] = (30, 30, 30)


MODEL_BASED_TAB_LAYOUT = {
    "reactions_combo": {"min_width": 200, "min_height": 30},
    "reaction_type_combo": {"min_width": 100, "min_height": 30},
    "range_calc_widget": {"min_height": 45},
    "reaction_table": {"min_height": 90},
    "adjusting_settings_box": {"min_height": 180},
    "models_scene": {"min_width": 200, "min_height": 150},
    "calc_buttons": {"button_width": 80, "button_height": 30},
}


class ReactionTable(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(3, 4, parent)
        self.setHorizontalHeaderLabels(["Parameter", "Value", "Min", "Max"])

        self.setColumnHidden(2, True)
        self.setColumnHidden(3, True)

        self.setItem(0, 0, QTableWidgetItem("Ea, kJ"))
        self.activation_energy_edit = QLineEdit()
        self.setCellWidget(0, 1, self.activation_energy_edit)
        self.ea_min_item = QLineEdit()
        self.setCellWidget(0, 2, self.ea_min_item)
        self.ea_max_item = QLineEdit()
        self.setCellWidget(0, 3, self.ea_max_item)

        self.setItem(1, 0, QTableWidgetItem("log(A)"))
        self.log_a_edit = QLineEdit()
        self.setCellWidget(1, 1, self.log_a_edit)
        self.log_a_min_item = QLineEdit()
        self.setCellWidget(1, 2, self.log_a_min_item)
        self.log_a_max_item = QLineEdit()
        self.setCellWidget(1, 3, self.log_a_max_item)

        self.setItem(2, 0, QTableWidgetItem("contribution"))
        self.contribution_edit = QLineEdit()
        self.setCellWidget(2, 1, self.contribution_edit)
        self.contribution_min_item = QLineEdit()
        self.setCellWidget(2, 2, self.contribution_min_item)
        self.contribution_max_item = QLineEdit()
        self.setCellWidget(2, 3, self.contribution_max_item)

        self.defaults = ReactionDefaults()

    def set_ranges_visible(self, visible: bool):
        self.setColumnHidden(2, not visible)
        self.setColumnHidden(3, not visible)

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

        self.activation_energy_edit.setText(str(reaction_data.get("Ea", self.defaults.Ea_default)))
        self.log_a_edit.setText(str(reaction_data.get("log_A", self.defaults.log_A_default)))
        self.contribution_edit.setText(str(reaction_data.get("contribution", self.defaults.contribution_default)))

        self.ea_min_item.setText(str(reaction_data.get("Ea_min", self.defaults.Ea_range[0])))
        self.ea_max_item.setText(str(reaction_data.get("Ea_max", self.defaults.Ea_range[1])))

        self.log_a_min_item.setText(str(reaction_data.get("log_A_min", self.defaults.log_A_range[0])))
        self.log_a_max_item.setText(str(reaction_data.get("log_A_max", self.defaults.log_A_range[1])))

        self.contribution_min_item.setText(
            str(reaction_data.get("contribution_min", self.defaults.contribution_range[0]))
        )
        self.contribution_max_item.setText(
            str(reaction_data.get("contribution_max", self.defaults.contribution_range[1]))
        )


class AdjustmentRowWidget(QWidget):
    valueChanged = pyqtSignal(str, float)  # передаём имя параметра и новое значение

    def __init__(self, parameter_name: str, initial_value: float, button_step: float, slider_scale: float, parent=None):
        super().__init__(parent)
        self.parameter_name = parameter_name
        self.base_value = initial_value
        self.button_step = button_step
        self.slider_scale = slider_scale

        layout = QVBoxLayout(self)
        self.value_label = QLabel(f"{self.base_value:.3f}")
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.value_label)

        h_layout = QHBoxLayout()
        const = AdjustmentDefaults()
        self.left_button = QPushButton("<")
        self.left_button.setFixedSize(const.BUTTON_SIZE, const.BUTTON_SIZE)
        self.left_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(const.SLIDER_MIN, const.SLIDER_MAX)
        self.slider.setValue(0)
        self.slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.slider.setTickInterval(const.SLIDER_TICK_INTERVAL)
        self.slider.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.right_button = QPushButton(">")
        self.right_button.setFixedSize(const.BUTTON_SIZE, const.BUTTON_SIZE)
        self.right_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        h_layout.addWidget(self.left_button)
        h_layout.addWidget(self.slider)
        h_layout.addWidget(self.right_button)
        layout.addLayout(h_layout)

        self.left_button.clicked.connect(self.on_left_clicked)
        self.right_button.clicked.connect(self.on_right_clicked)
        self.slider.valueChanged.connect(self.on_slider_value_changed)
        self.slider.sliderReleased.connect(self.on_slider_released)

    def on_left_clicked(self):
        self.base_value -= self.button_step
        self.slider.setValue(0)  # сброс ползунка
        self.update_label()
        self.valueChanged.emit(self.parameter_name, self.base_value)

    def on_right_clicked(self):
        self.base_value += self.button_step
        self.slider.setValue(0)
        self.update_label()
        self.valueChanged.emit(self.parameter_name, self.base_value)

    def on_slider_value_changed(self, value):
        potential_value = self.base_value + (value * self.slider_scale)
        self.value_label.setText(f"{potential_value:.3f}")

    def on_slider_released(self):
        offset = self.slider.value() * self.slider_scale
        self.base_value += offset
        self.slider.setValue(0)
        self.update_label()
        self.valueChanged.emit(self.parameter_name, self.base_value)

    def update_label(self):
        self.value_label.setText(f"{self.base_value:.3f}")


class AdjustingSettingsBox(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        main_layout = QVBoxLayout(self)
        self.setLayout(main_layout)

        params = ReactionAdjustmentParameters()
        self.ea_adjuster = AdjustmentRowWidget(
            "Ea", params.ea_default, params.ea_button_step, params.ea_slider_scale, parent=self
        )
        self.log_a_adjuster = AdjustmentRowWidget(
            "log_A", params.log_a_default, params.log_a_button_step, params.log_a_slider_scale, parent=self
        )
        self.contrib_adjuster = AdjustmentRowWidget(
            "contribution",
            params.contribution_default,
            params.contribution_button_step,
            params.contribution_slider_scale,
            parent=self,
        )

        main_layout.addWidget(self.ea_adjuster)
        main_layout.addWidget(self.log_a_adjuster)
        main_layout.addWidget(self.contrib_adjuster)


class ModelCalcButtons(QWidget):
    simulation_started = pyqtSignal(dict)
    simulation_stopped = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_ref = parent
        self.is_calculating = False

        layout = QHBoxLayout(self)
        self.setLayout(layout)

        self.settings_button = QPushButton("Settings")
        self.start_button = QPushButton("Start")
        self.stop_button = QPushButton("Stop")

        layout.addWidget(self.settings_button)
        layout.addWidget(self.start_button)
        layout.addWidget(self.stop_button)

        self.stop_button.hide()

        self.settings_button.clicked.connect(self.open_settings_dialog)
        self.start_button.clicked.connect(self.check_and_start_simulation)
        self.stop_button.clicked.connect(self.stop_simulation)

    def open_settings_dialog(self):
        if hasattr(self.parent_ref, "open_settings"):
            self.parent_ref.open_settings()

    def check_and_start_simulation(self):
        scheme = {}
        if hasattr(self.parent_ref, "models_scene"):
            scheme = self.parent_ref.models_scene.get_reaction_scheme_as_json()

        data = {
            "operation": OperationType.MODEL_BASED_CALCULATION,
            "scheme": scheme,
        }

        self.simulation_started.emit(data)
        self.start_simulation()

    def start_simulation(self):
        self.is_calculating = True
        self.layout().replaceWidget(self.start_button, self.stop_button)
        self.start_button.hide()
        self.stop_button.show()

    def stop_simulation(self):
        if self.is_calculating:
            self.simulation_stopped.emit({"operation": OperationType.STOP_CALCULATION})
            self.is_calculating = False
            self.layout().replaceWidget(self.stop_button, self.start_button)
            self.stop_button.hide()
            self.start_button.show()


class RangeAndCalculateWidget(QWidget):
    showRangeToggled = pyqtSignal(bool)
    calculateToggled = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        self.setLayout(layout)

        self.showRangeCheckbox = QCheckBox("Show Range")
        self.calculateCheckbox = QCheckBox("Calculate")

        layout.addWidget(self.showRangeCheckbox)
        layout.addWidget(self.calculateCheckbox)

        self.showRangeCheckbox.stateChanged.connect(
            lambda state: self.showRangeToggled.emit(state == Qt.CheckState.Checked)
        )
        self.calculateCheckbox.stateChanged.connect(
            lambda state: self.calculateToggled.emit(state == Qt.CheckState.Checked)
        )


class ModelBasedTab(QWidget):
    model_params_changed = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scheme_data = {}
        self._reactions_list = []
        self._calculation_method = None
        self._calculation_method_params = {}

        main_layout = QVBoxLayout(self)
        self.setLayout(main_layout)

        self.reactions_combo = QComboBox()
        rc = MODEL_BASED_TAB_LAYOUT["reactions_combo"]
        self.reactions_combo.setMinimumSize(rc["min_width"], rc["min_height"])
        main_layout.addWidget(self.reactions_combo)

        reaction_type_layout = QHBoxLayout()
        reaction_type_label = QLabel("Reaction type:")
        self.reaction_type_combo = QComboBox()
        rc2 = MODEL_BASED_TAB_LAYOUT["reaction_type_combo"]
        self.reaction_type_combo.setMinimumSize(rc2["min_width"], rc2["min_height"])
        self.reaction_type_combo.addItems(NUC_MODELS_LIST)

        reaction_type_layout.addWidget(reaction_type_label)
        reaction_type_layout.addWidget(self.reaction_type_combo)
        main_layout.addLayout(reaction_type_layout)

        self.range_calc_widget = RangeAndCalculateWidget()
        rc3 = MODEL_BASED_TAB_LAYOUT.get("range_calc_widget", {})
        if "min_height" in rc3:
            self.range_calc_widget.setMinimumHeight(rc3["min_height"])
        self.range_calc_widget.showRangeToggled.connect(self.on_show_range_checkbox_changed)
        self.range_calc_widget.calculateToggled.connect(self.on_calculate_toggled)
        main_layout.addWidget(self.range_calc_widget)

        self.reaction_table = ReactionTable()
        rc4 = MODEL_BASED_TAB_LAYOUT.get("reaction_table", {})
        if "min_height" in rc4:
            self.reaction_table.setMinimumHeight(rc4["min_height"])
        main_layout.addWidget(self.reaction_table)

        layout_settings = LayoutSettings()
        for col, width in enumerate(layout_settings.reaction_table_column_widths):
            self.reaction_table.setColumnWidth(col, width)
        for row, height in enumerate(layout_settings.reaction_table_row_heights):
            self.reaction_table.setRowHeight(row, height)

        self.adjusting_settings_box = AdjustingSettingsBox()
        rc5 = MODEL_BASED_TAB_LAYOUT.get("adjusting_settings_box", {})
        if "min_height" in rc5:
            self.adjusting_settings_box.setMinimumHeight(rc5["min_height"])
        main_layout.addWidget(self.adjusting_settings_box)

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

        self.adjusting_settings_box.ea_adjuster.valueChanged.connect(self.on_adjuster_value_changed)
        self.adjusting_settings_box.log_a_adjuster.valueChanged.connect(self.on_adjuster_value_changed)
        self.adjusting_settings_box.contrib_adjuster.valueChanged.connect(self.on_adjuster_value_changed)

        bottom_layout = QVBoxLayout()
        self.models_scene = ModelsScheme(self)
        rc6 = MODEL_BASED_TAB_LAYOUT.get("models_scene", {})
        if "min_width" in rc6 and "min_height" in rc6:
            self.models_scene.setMinimumSize(rc6["min_width"], rc6["min_height"])
        bottom_layout.addWidget(self.models_scene)

        self.calc_buttons = ModelCalcButtons(self)
        rc7 = MODEL_BASED_TAB_LAYOUT.get("calc_buttons", {})
        if "button_width" in rc7 and "button_height" in rc7:
            self.calc_buttons.settings_button.setFixedSize(rc7["button_width"], rc7["button_height"])
            self.calc_buttons.start_button.setFixedSize(rc7["button_width"], rc7["button_height"])
            self.calc_buttons.stop_button.setFixedSize(rc7["button_width"], rc7["button_height"])
        bottom_layout.addWidget(self.calc_buttons)

        main_layout.addLayout(bottom_layout)

    def on_adjuster_value_changed(self, parameter_name: str, new_value: float):
        if parameter_name == "Ea":
            self.reaction_table.activation_energy_edit.setText(str(new_value))
        elif parameter_name == "log_A":
            self.reaction_table.log_a_edit.setText(str(new_value))
        elif parameter_name == "contribution":
            self.reaction_table.contribution_edit.setText(str(new_value))
        self._on_params_changed()

    def on_show_range_checkbox_changed(self, checked: bool):
        self.reaction_table.set_ranges_visible(checked)

    def on_calculate_toggled(self, checked: bool):
        pass

    def update_scheme_data(self, scheme_data: dict):
        self._scheme_data = scheme_data
        self._reactions_list = scheme_data.get("reactions", [])

        current_label = self.reactions_combo.currentText() if self.reactions_combo.count() > 0 else None

        self.reactions_combo.clear()
        reaction_map = {}
        for i, reaction in enumerate(self._reactions_list):
            label = f"{reaction.get('from', '?')} -> {reaction.get('to', '?')}"
            self.reactions_combo.addItem(label)
            reaction_map[label] = i

        default_label = "A -> B"
        new_index = reaction_map.get(current_label, reaction_map.get(default_label, 0))

        if not self._reactions_list:
            self.reaction_table.update_table({})
        else:
            self.reactions_combo.setCurrentIndex(new_index)
            self._on_reactions_combo_changed(new_index)

        self.models_scene.update_from_scheme(scheme_data, self._reactions_list)

    def update_calculation_settings(self, calculation_settings: dict):
        self._calculation_method = calculation_settings.get("method")
        self._calculation_method_params = calculation_settings.get("method_parameters")

    def _on_reactions_combo_changed(self, index: int):
        if 0 <= index < len(self._reactions_list):
            reaction_data = self._reactions_list[index]
            self.reaction_table.update_table(reaction_data)

            # Обновляем значения в слайдерах согласно выбранной реакции
            default_reaction = ReactionDefaults()
            ea_value = reaction_data.get("Ea", default_reaction.Ea_default)
            log_a_value = reaction_data.get("log_A", default_reaction.log_A_default)
            contrib_value = reaction_data.get("contribution", default_reaction.contribution_default)

            self.adjusting_settings_box.ea_adjuster.base_value = ea_value
            self.adjusting_settings_box.ea_adjuster.slider.setValue(0)
            self.adjusting_settings_box.ea_adjuster.update_label()

            self.adjusting_settings_box.log_a_adjuster.base_value = log_a_value
            self.adjusting_settings_box.log_a_adjuster.slider.setValue(0)
            self.adjusting_settings_box.log_a_adjuster.update_label()

            self.adjusting_settings_box.contrib_adjuster.base_value = contrib_value
            self.adjusting_settings_box.contrib_adjuster.slider.setValue(0)
            self.adjusting_settings_box.contrib_adjuster.update_label()

            new_reaction_type = reaction_data.get("reaction_type", "F2")
            current_reaction_type = self.reaction_type_combo.currentText()
            if new_reaction_type != current_reaction_type:
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
            ea_min_val = self.reaction_table.defaults.Ea_range[0]

        try:
            ea_max_val = float(self.reaction_table.ea_max_item.text())
        except ValueError:
            ea_max_val = self.reaction_table.defaults.Ea_range[1]

        try:
            loga_min_val = float(self.reaction_table.log_a_min_item.text())
        except ValueError:
            loga_min_val = self.reaction_table.defaults.log_A_range[0]

        try:
            loga_max_val = float(self.reaction_table.log_a_max_item.text())
        except ValueError:
            loga_max_val = self.reaction_table.defaults.log_A_range[1]

        try:
            contrib_min_val = float(self.reaction_table.contribution_min_item.text())
        except ValueError:
            contrib_min_val = self.reaction_table.defaults.contribution_range[0]

        try:
            contrib_max_val = float(self.reaction_table.contribution_max_item.text())
        except ValueError:
            contrib_max_val = self.reaction_table.defaults.contribution_range[1]

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

        update_data = {
            "operation": OperationType.MODEL_PARAMS_CHANGE,
            "reaction_scheme": new_scheme,
            "is_calculate": True if self.range_calc_widget.calculateCheckbox.isChecked() else None,
        }
        self.model_params_changed.emit(update_data)

    def open_settings(self):
        if not self._reactions_list:
            QMessageBox.information(self, "No Reactions", "There are no available reactions to configure.")
            return

        dialog = CalculationSettingsDialog(
            self._reactions_list, self._calculation_method, self._calculation_method_params, parent=self
        )
        if dialog.exec():
            new_calculation_settings, updated_reactions = dialog.get_data()

            self._reactions_list = updated_reactions

            if self._scheme_data and "reactions" in self._scheme_data:
                for i, r in enumerate(self._scheme_data["reactions"]):
                    if i < len(updated_reactions):
                        self._scheme_data["reactions"][i] = updated_reactions[i]

            update_data = {
                "operation": OperationType.MODEL_PARAMS_CHANGE,
                "reaction_scheme": self._scheme_data,
                "calculation_settings": new_calculation_settings,
                "is_calculate": True if self.range_calc_widget.calculateCheckbox.isChecked() else None,
            }
            self.model_params_changed.emit(update_data)

            QMessageBox.information(self, "Settings Saved", "The settings have been updated successfully.")


class SelectFileDataDialog(QDialog):
    def __init__(self, df_copies, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Files for Series")
        self.selected_files = []
        self.checkboxes = []
        self.rate_line_edits = []
        self.mass_line_edits = []

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

            rate_line_edit = QLineEdit()
            rate_line_edit.setPlaceholderText("Enter heating rate")

            mass_line_edit = QLineEdit()
            mass_line_edit.setPlaceholderText("Enter mass")

            file_layout.addWidget(checkbox)
            file_layout.addWidget(rate_line_edit)
            file_layout.addWidget(mass_line_edit)
            scroll_layout.addLayout(file_layout)

            self.checkboxes.append(checkbox)
            self.rate_line_edits.append(rate_line_edit)
            self.mass_line_edits.append(mass_line_edit)

        scroll_content.setLayout(scroll_layout)
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

        button_box = QHBoxLayout()
        self.ok_button = QPushButton("OK")
        self.cancel_button = QPushButton("Cancel")
        button_box.addWidget(self.ok_button)
        button_box.addWidget(self.cancel_button)
        layout.addLayout(button_box)

        self.setLayout(layout)

        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

    def get_selected_files(self):
        series_name = self.series_name_line_edit.text().strip()
        if not series_name:
            QMessageBox.warning(self, "Invalid Input", "Please enter a series name.")
            return None, []

        selected_files = []
        for checkbox, rate_line_edit, mass_line_edit in zip(
            self.checkboxes, self.rate_line_edits, self.mass_line_edits
        ):
            if checkbox.isChecked():
                rate_text = rate_line_edit.text().strip()
                mass_text = mass_line_edit.text().strip()

                if not rate_text:
                    QMessageBox.warning(self, "Invalid Input", f"Please enter a heating rate for '{checkbox.text()}'")
                    return None, []

                if not mass_text:
                    QMessageBox.warning(self, "Invalid Input", f"Please enter a mass for '{checkbox.text()}'")
                    return None, []

                try:
                    heating_rate = float(rate_text)
                except ValueError:
                    QMessageBox.warning(
                        self, "Invalid Input", f"Please enter a valid number heating rate for '{checkbox.text()}'"
                    )
                    return None, []

                try:
                    mass = float(mass_text)
                except ValueError:
                    QMessageBox.warning(
                        self, "Invalid Input", f"Please enter a valid number mass for '{checkbox.text()}'"
                    )
                    return None, []

                selected_files.append((checkbox.text(), heating_rate, mass))

        return series_name, selected_files


class CalculationSettingsDialog(QDialog):
    def __init__(
        self, reactions_data: list[dict], calculation_method: str, calculation_method_params: dict, parent=None
    ):
        super().__init__(parent)
        self.calculation_method = calculation_method
        self.calculation_method_params = calculation_method_params
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

        for param_name, default_value in self.calculation_method_params.items():
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
            combo_type.addItems(NUC_MODELS_LIST)
            current_type = reaction.get("reaction_type", "F2")
            if current_type in NUC_MODELS_LIST:
                combo_type.setCurrentText(current_type)
            top_line_layout.addWidget(combo_type)

            box_layout.addWidget(top_line_widget)

            table = QTableWidget(3, 2, self)
            table.setHorizontalHeaderLabels(["Min", "Max"])
            table.setVerticalHeaderLabels(["Ea", "log(A)", "contribution"])
            table.setEditTriggers(QAbstractItemView.EditTrigger.AllEditTriggers)
            table.verticalHeader().setVisible(True)
            table.horizontalHeader().setVisible(True)
            table.setStyleSheet("""
                QTableWidget::item:selected {
                    background-color: lightgray;
                    color: black;
                }
                QTableWidget::item:focus {
                    background-color: lightgray;
                    color: black;
                }
            """)
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
                    default_value = self.calculation_method_params[key]
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

        return {"method": selected_method, "method_parameters": method_params}, updated_reactions

    def accept(self):
        data_result, reactions = self.get_data()
        if data_result is None or reactions is None:
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
                    return False, "Must be non-negative."
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
                    return False, "Must be non-negative."
            elif key == "updating":
                options = self.get_options_for_parameter("updating")
                if value not in options:
                    return False, f"Must be one of {options}."
            elif key == "workers":
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
