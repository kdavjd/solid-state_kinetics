import json
import os
from collections import defaultdict

import numpy as np
from core.basic_signals import BasicSignals
from core.logger_config import logger
from core.logger_console import LoggerConsole as console
from PyQt6.QtCore import pyqtSignal, pyqtSlot
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


class FileTransferButtons(QWidget, BasicSignals):
    request_signal = pyqtSignal(dict)

    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        # После добавления сигналов при первом выборе вкладки деконволюции происходит
        # непрусмотренное выскакивание окна на долю секунды
        BasicSignals.__init__(self, actor_name="file_tansfer_buttons")
        self.layout = QVBoxLayout(self)

        self.load_reactions_button = QPushButton("Импорт")
        self.export_reactions_button = QPushButton("Экспорт")
        self.buttons_layout = QHBoxLayout()
        self.buttons_layout.addWidget(self.load_reactions_button)
        self.buttons_layout.addWidget(self.export_reactions_button)
        self.layout.addLayout(self.buttons_layout)

        self.load_reactions_button.clicked.connect(self.load_reactions)
        self.export_reactions_button.clicked.connect(self.export_reactions)

    @pyqtSlot(dict)
    def response_slot(self, params: dict):
        super().response_slot(params)

    def load_reactions(self):
        load_file_name, _ = QFileDialog.getOpenFileName(
            self, "Выберите JSON файл для импорта данных", "", "JSON Files (*.json)"
        )

        if load_file_name:
            with open(load_file_name, "r", encoding="utf-8") as file:
                data = json.load(file)

            for reaction_key, reaction_data in data.items():
                if "x" in reaction_data:
                    reaction_data["x"] = np.array(reaction_data["x"])

            request_id = self.create_and_emit_request("main_tab", "get_file_name")
            file_name = self.handle_response_data(request_id)
            logger.debug(f"Current file_name: {file_name}")

            request_id = self.create_and_emit_request(
                "calculations_data", "set_value", path_keys=[file_name], value=data
            )
            self.handle_response_data(request_id)

            console.log(f"Данные успешно импортированы из файла:\n\n{load_file_name}")
            logger.info(f"Данные успешно импортированы из файла: {load_file_name}")

            request_id = self.create_and_emit_request("main_tab", "update_reaction_table", reactions_data=data)
            self.handle_response_data(request_id)

    def _generate_suggested_file_name(self, file_name: str, data: dict):
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

    def export_reactions(self):
        request_id = self.create_and_emit_request("main_tab", "get_file_name")
        file_name = self.handle_response_data(request_id)
        logger.debug(f"file_name: {file_name}")

        request_id = self.create_and_emit_request("calculations_data", "get_value", path_keys=[file_name])
        data = self.handle_response_data(request_id)
        logger.debug(f"data: {data}")

        suggested_file_name = self._generate_suggested_file_name(file_name, data)

        save_file_name, _ = QFileDialog.getSaveFileName(
            self, "Выберите место для сохранения JSON файла", suggested_file_name, "JSON Files (*.json)"
        )

        if save_file_name:
            with open(save_file_name, "w", encoding="utf-8") as file:
                json.dump(data, file, ensure_ascii=False, indent=4, cls=NumpyArrayEncoder)
                console.log(f"Данные успешно экспортированы в файл:\n\n{save_file_name}")
                logger.info(f"Данные успешно экспортированы в файл:{save_file_name}")


class NumpyArrayEncoder(json.JSONEncoder):
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

        self.add_reaction_button = QPushButton("Добавить")
        self.del_reaction_button = QPushButton("Удалить")
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

        self.settings_button = QPushButton("Настрйоки расчета")
        self.layout.addWidget(self.settings_button)

        self.add_reaction_button.clicked.connect(self.add_reaction)
        self.del_reaction_button.clicked.connect(self.del_reaction)
        self.settings_button.clicked.connect(self.open_settings)

    def switch_file(self, file_name):
        if file_name not in self.reactions_tables:
            self.reactions_tables[file_name] = QTableWidget()
            self.reactions_tables[file_name].setColumnCount(2)
            self.reactions_tables[file_name].setHorizontalHeaderLabels(["Имя", "Функция"])
            self.reactions_tables[file_name].horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            self.reactions_tables[file_name].itemClicked.connect(self.selected_reaction)
            self.layout.addWidget(self.reactions_tables[file_name])

        if self.active_file:
            self.reactions_tables[self.active_file].setVisible(False)

        self.reactions_tables[file_name].setVisible(True)
        self.active_file = file_name

    def function_changed(self, reaction_name, combo):
        function = combo.currentText()
        data_change = {
            "path_keys": [reaction_name, "function"],
            "operation": "update_value",
            "value": function,
        }
        self.reaction_function_changed.emit(data_change)
        logger.debug(f"Изменена реакция для {reaction_name}: {function}")

    def add_reaction(self, checked=False, reaction_name=None, function_name=None, emit_signal=True):
        if not self.active_file:
            QMessageBox.warning(self, "Ошибка", "Файл не выбран.")
            return

        table = self.reactions_tables[self.active_file]
        row_count = table.rowCount()
        table.insertRow(row_count)

        if reaction_name is None:
            reaction_name = f"reaction_{self.reactions_counters[self.active_file]}"
        else:
            try:
                counter_value = int(reaction_name.split("_")[-1])
                self.reactions_counters[self.active_file] = max(
                    self.reactions_counters[self.active_file], counter_value + 1
                )
            except ValueError:
                logger.error(f"Неверный формат имени реакции: {reaction_name}")

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
            reaction_data = {"path_keys": [reaction_name], "operation": "add_reaction"}
            self.reaction_added.emit(reaction_data)

        self.reactions_counters[self.active_file] += 1

    def on_fail_add_reaction(self):
        if not self.active_file:
            logger.debug("Файл не выбран. Откат операции добавления невозможен.")
            return

        table = self.reactions_tables[self.active_file]
        if table.rowCount() > 0:
            last_row = table.rowCount() - 1
            table.removeRow(last_row)
            self.reactions_counters[self.active_file] -= 1
            logger.debug("Неудачное добавление реакции. Удалена последняя строка.")

    def del_reaction(self):
        if not self.active_file:
            QMessageBox.warning(self, "Удаление Реакции", "Файл не выбран.")
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
                    "operation": "remove_reaction",
                }
                self.reaction_removed.emit(reaction_data)
            else:
                logger.debug("Попытка удалить пустую ячейку.")
        else:
            QMessageBox.warning(self, "Удаление Реакции", "В списке нет реакций для удаления.")

    def selected_reaction(self, item):
        row = item.row()
        reaction_name = self.reactions_tables[self.active_file].item(row, 0).text()
        self.active_reaction = reaction_name
        logger.debug(f"Активная реакция: {reaction_name}")
        self.reaction_chosed.emit({"path_keys": [reaction_name], "operation": "highlight_reaction"})

    def open_settings(self):
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

                empty_keys = [key for key, value in selected_functions.items() if not value]
                if empty_keys:
                    QMessageBox.warning(
                        self,
                        "Ошибка настроек",
                        f"{', '.join(empty_keys)} должна описываться хотя бы одной функцией.",
                    )
                    self.open_settings()
                    return

                self.calculation_settings[self.active_file] = selected_functions
                self.deconvolution_settings[self.active_file] = {
                    "method": selected_method,
                    "deconvolution_parameters": deconvolution_parameters,
                }
                logger.debug(f"Выбранные функции: {selected_functions}")
                logger.debug(f"Настройки деконволюции: {self.deconvolution_settings[self.active_file]}")

                formatted_functions = "\n".join([f"{key}: {value}" for key, value in selected_functions.items()])
                message = f"    {self.active_file}\n{formatted_functions}"

                QMessageBox.information(self, "Настройки расчета", f"Настройки обновлены для:\n{message}")
        else:
            QMessageBox.warning(self, "Настройки расчета", "Файл не выбран.")


class CalculationSettingsDialog(QDialog):
    def __init__(self, reactions, initial_settings, initial_deconvolution_settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройки расчета")
        self.reactions = reactions
        self.initial_settings = initial_settings
        self.initial_deconvolution_settings = initial_deconvolution_settings
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        reactions_group_box = QGroupBox("Выбор функций реакций")
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

        deconvolution_group_box = QGroupBox("Параметры деконволюции")
        deconvolution_layout = QVBoxLayout()
        deconvolution_group_box.setLayout(deconvolution_layout)

        method_layout = QHBoxLayout()
        method_label = QLabel("Метод деконволюции:")
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
            for key, value in DIFFERENTIAL_EVOLUTION_DEFAULT_KWARGS.items():
                label = QLabel(key)
                tooltip = self.get_tooltip_for_parameter(key)
                label.setToolTip(tooltip)
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
            pass

    def get_tooltip_for_parameter(self, param_name):
        tooltips = {
            "strategy": "Стратегия дифференциальной эволюции. Выберите один из доступных вариантов.",
            "maxiter": "Максимальное количество итераций. Целое число >= 1.",
            "popsize": "Размер популяции. Целое число >= 1.",
            "tol": "Относительная точность для критериев остановки. Положительное число.",
            "mutation": "Коэффициент мутации. Число или кортеж из двух чисел в диапазоне [0, 2].",
            "recombination": "Коэффициент рекомбинации. Число в диапазоне [0, 1].",
            "seed": "Зерно для генератора случайных чисел. Целое число или оставьте пустым.",
            "callback": "Функция обратного вызова. Оставьте пустым, если не требуется.",
            "disp": "Отображать статус при оптимизации.",
            "polish": "Производить ли окончательную оптимизацию при завершении дифференциальной эволюции.",
            "init": "Метод инициализации популяции.",
            "atol": "Абсолютная точность для критериев остановки. Положительное число.",
            "updating": "Режим обновления популяции: immediate или deferred.",
            "workers": "Количество процессов для параллельных вычислений. Целое число >= 1.",
            "constraints": "Ограничения для задачи оптимизации. Оставьте пустым, если не требуется.",
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
        selected_functions = {}
        for reaction_name, checkboxes in self.checkboxes.items():
            selected_functions[reaction_name] = [cb.text() for cb in checkboxes if cb.isChecked()]
        selected_method, deconvolution_parameters = self.get_deconvolution_parameters()
        return selected_functions, selected_method, deconvolution_parameters

    def get_deconvolution_parameters(self):
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
                    default_value = DIFFERENTIAL_EVOLUTION_DEFAULT_KWARGS[key]
                    value = self.convert_to_type(text, default_value)

                    is_valid, error_msg = self.validate_parameter(key, value)
                    if not is_valid:
                        errors.append(f"Параметр '{key}': {error_msg}")
                    parameters[key] = value
            if errors:
                error_message = "\n".join(errors)
                QMessageBox.warning(self, "Ошибка ввода параметров", error_message)
                return None, None
        elif selected_method == "another_method":
            parameters = {}
        return selected_method, parameters

    def convert_to_type(self, text, default_value):
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
        try:
            if key == "strategy":
                strategies = self.get_options_for_parameter("strategy")
                if value not in strategies:
                    return False, f"Недопустимая стратегия. Выберите из {strategies}."
            elif key == "maxiter":
                if not isinstance(value, int) or value < 1:
                    return False, "Должно быть целым числом >= 1."
            elif key == "popsize":
                if not isinstance(value, int) or value < 1:
                    return False, "Должно быть целым числом >= 1."
            elif key == "tol":
                if not isinstance(value, (int, float)) or value < 0:
                    return False, "Должно быть неотрицательным числом."
            elif key == "mutation":
                if isinstance(value, tuple):
                    if len(value) != 2 or not all(0 <= v <= 2 for v in value):
                        return False, "Должен быть кортежем из двух чисел в диапазоне [0, 2]."
                elif isinstance(value, (int, float)):
                    if not 0 <= value <= 2:
                        return False, "Должно быть числом в диапазоне [0, 2]."
                else:
                    return False, "Неверный формат."
            elif key == "recombination":
                if not isinstance(value, (int, float)) or not 0 <= value <= 1:
                    return False, "Должно быть числом в диапазоне [0, 1]."
            elif key == "seed":
                if not (isinstance(value, int) or value is None):
                    return False, "Должно быть целым числом или пустым."
            elif key == "atol":
                if not isinstance(value, (int, float)) or value < 0:
                    return False, "Должно быть неотрицательным числом."
            elif key == "updating":
                options = self.get_options_for_parameter("updating")
                if value not in options:
                    return False, f"Должно быть одним из {options}."
            elif key == "workers":
                if not isinstance(value, int) or value < 1:
                    return False, "Должно быть целым числом >= 1."

            return True, ""
        except Exception as e:
            return False, f"Ошибка при проверке параметра: {str(e)}"

    def accept(self):
        selected_functions = {}
        for reaction_name, checkboxes in self.checkboxes.items():
            selected = [cb.text() for cb in checkboxes if cb.isChecked()]
            if not selected:
                QMessageBox.warning(
                    self, "Ошибка настроек", f"Реакция '{reaction_name}' должна иметь хотя бы одну функцию."
                )
                return
            selected_functions[reaction_name] = selected

        selected_method, deconvolution_parameters = self.get_deconvolution_parameters()
        if deconvolution_parameters is None:
            # Если произошла ошибка в параметрах, не закрываем диалог
            return
        self.selected_functions = selected_functions
        self.selected_method = selected_method
        self.deconvolution_parameters = deconvolution_parameters
        super().accept()

    def get_results(self):
        return self.selected_functions, self.selected_method, self.deconvolution_parameters


class CoeffsTable(QTableWidget):
    update_value = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(5, 2, parent)
        self.header_labels = ["от", "до"]
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
        row_height = self.rowHeight(0)
        borders_height = len(self.default_row_labels) * 2
        header_height = self.horizontalHeader().height()
        total_height = (row_height * len(self.default_row_labels)) + header_height + borders_height
        self.setFixedHeight(total_height)

    def mock_table(self):
        for i in range(len(self.default_row_labels)):
            for j in range(len(self.header_labels)):
                self.setItem(i, j, QTableWidgetItem("NaN"))

    def fill_table(self, reaction_params: dict):
        logger.debug(f"Приняты параметры реакции для таблицы {reaction_params}")
        param_keys = ["lower_bound_coeffs", "upper_bound_coeffs"]
        function_type = reaction_params[param_keys[0]][1]
        if function_type not in self.row_labels_dict:
            logger.error(f"Неизвестный тип функции: {function_type}")
            return

        self._is_table_filling = True
        row_labels = self.row_labels_dict[function_type]
        self.setRowCount(len(row_labels))
        self.setVerticalHeaderLabels(row_labels)

        for j, key in enumerate(param_keys):
            try:
                data = reaction_params[key][2]  # структура ключей: x_range, function_type, params
                for i in range(min(len(row_labels), len(data))):
                    value = f"{data[i]:.2f}"
                    self.setItem(i, j, QTableWidgetItem(value))
            except IndexError as e:
                logger.error(f"Ошибка индекса при обработке данных '{key}': {e}")

        self.mock_remaining_cells(len(row_labels))
        self._is_table_filling = False

    def mock_remaining_cells(self, num_rows):
        for i in range(num_rows, len(self.default_row_labels)):
            for j in range(len(self.header_labels)):
                self.setItem(i, j, QTableWidgetItem("NaN"))

    def update_reaction_params(self, row, column):
        if not self._is_table_filling:
            try:
                item = self.item(row, column)
                value = float(item.text())
                row_label = self.verticalHeaderItem(row).text()
                column_label = self.horizontalHeaderItem(column).text()

                path_keys = [self.column_to_bound(column_label), row_label]
                data_change = {
                    "path_keys": path_keys,
                    "operation": "update_value",
                    "value": value,
                }
                self.update_value.emit(data_change)
            except ValueError as e:
                console.log(f"Неверные данные для преобразования в число: ряд {row+1}, колонка {column+1}")
                logger.error(f"Неверные данные для преобразования в число: ряд {row}, колонка {column}: {e}")

    def column_to_bound(self, column_label):
        return {"от": "lower_bound_coeffs", "до": "upper_bound_coeffs"}.get(column_label, "")


class CalcButtons(QWidget):
    calculation_started = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.start_button = QPushButton("Начать расчет")
        self.stop_button = QPushButton("Остановить расчет")
        self.layout.addWidget(self.start_button)

        self.start_button.clicked.connect(self.check_and_start_calculation)
        self.stop_button.clicked.connect(self.stop_calculation)
        self.is_calculating = False
        self.parent = parent

    def check_and_start_calculation(self):
        if not self.parent.reactions_table.active_file:
            QMessageBox.warning(self, "Ошибка", "Файл не выбран.")
            return

        settings = self.parent.reactions_table.calculation_settings.get(self.parent.reactions_table.active_file, {})
        deconvolution_settings = self.parent.reactions_table.deconvolution_settings.get(
            self.parent.reactions_table.active_file, {}
        )
        if not settings or not deconvolution_settings:
            QMessageBox.information(self, "Настройки обязательны.", "Настройки расчета не установлены.")
            self.parent.open_settings_dialog()
        else:
            data = {
                "path_keys": [],
                "operation": "deconvolution",
                "chosen_functions": settings,
                "deconvolution_settings": deconvolution_settings,
            }
            self.calculation_started.emit(data)
            self.start_calculation()

    def start_calculation(self):
        self.is_calculating = True
        self.layout.replaceWidget(self.start_button, self.stop_button)
        self.start_button.hide()
        self.stop_button.show()

    def stop_calculation(self):
        self.is_calculating = False
        self.layout.replaceWidget(self.stop_button, self.start_button)
        self.stop_button.hide()
        self.start_button.show()


class DeconvolutionSubBar(QWidget, BasicSignals):
    update_value = pyqtSignal(dict)

    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        BasicSignals.__init__(self, actor_name="deconvolution_sub_bar")
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
        if self.reactions_table.active_reaction:
            data["path_keys"].insert(0, self.reactions_table.active_reaction)
            self.update_value.emit(data)
        else:
            console.log("Для изменения значения выберите реакцию.")

    def handle_update_function_value(self, data: dict):
        if self.reactions_table.active_reaction is not None:
            self.update_value.emit(data)

    def open_settings_dialog(self):
        self.reactions_table.open_settings()

    def get_reactions_for_file(self, file_name):
        table = self.reactions_table.reactions_tables[file_name]
        reactions = {}
        for row in range(table.rowCount()):
            reaction_name = table.item(row, 0).text()
            combo = table.cellWidget(row, 1)
            reactions[reaction_name] = combo
        return reactions
