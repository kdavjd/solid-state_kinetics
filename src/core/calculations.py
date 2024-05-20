from functools import lru_cache

import numpy as np
import pandas as pd
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

from core.calculations_data import CalculationsData
from core.curve_fitting import CurveFitting as cft
from core.file_data import FileData
from core.logger_config import logger
from core.logger_console import LoggerConsole as console


class Calculations(QObject):
    plot_reaction = pyqtSignal(tuple, list)
    add_reaction_fail = pyqtSignal()
    reaction_params_to_gui = pyqtSignal(dict)

    def __init__(self, file_data: FileData, calculations_data: CalculationsData):
        super().__init__()
        self.file_data = file_data
        self.calculations_data = calculations_data

    def extract_reaction_params(self, path_keys: list):
        reaction_params = self.calculations_data.get_value(path_keys)
        x: np.ndarray = reaction_params.get('x')
        function_type: str = reaction_params.get('function')
        coeffs: dict = reaction_params.get('coeffs', {})
        upper_coeffs: dict = reaction_params.get('upper_bound_coeffs', {})
        lower_coeffs: dict = reaction_params.get('lower_bound_coeffs', {})

        x_range = (np.min(x), np.max(x))

        default_keys = ['h', 'z', 'w']
        function_specific_keys = {
            'fraser': default_keys + ['fr'],
            'ads': default_keys + ['ads1', 'ads2']
        }
        allowed_keys = function_specific_keys.get(function_type, default_keys)

        coeffs_tuple = tuple(coeffs.get(key) for key in allowed_keys if key in coeffs)
        upper_coeffs_tuple = tuple(upper_coeffs.get(key) for key in allowed_keys if key in upper_coeffs)
        lower_coeffs_tuple = tuple(lower_coeffs.get(key) for key in allowed_keys if key in lower_coeffs)

        return {
            "coeffs": (x_range, function_type, coeffs_tuple),
            "upper_bound_coeffs": (x_range, function_type, upper_coeffs_tuple),
            "lower_bound_coeffs": (x_range, function_type, lower_coeffs_tuple)
        }

    @lru_cache(maxsize=128)
    def calculate_reaction(self, reaction_params: tuple):
        x_range, function_type, coeffs = reaction_params
        x = np.linspace(x_range[0], x_range[1], 100)
        result = None
        if function_type == "gauss":
            result = cft.gaussian(x, *coeffs)
        elif function_type == "fraser":
            result = cft.fraser_suzuki(x, *coeffs)
        elif function_type == "ads":
            result = cft.asymmetric_double_sigmoid(x, *coeffs)
        return result

    def diff_function(self, data: pd.DataFrame):
        return data.diff() * -1

    @pyqtSlot(dict)
    def modify_active_file_slot(self, params: dict):
        logger.debug(f"В modify_active_file_slot пришли данные {params}")
        operation = params.get("operation")
        file_name = params.get("file_name")
        if operation == "differential":
            if not self.file_data.check_operation_executed(file_name, operation):
                self.file_data.modify_data(self.diff_function, params)
            else:
                console.log("Данные уже приведены к da/dT")
        elif operation == "cancel_changes":
            self.file_data.reset_dataframe_copy(file_name)

    @pyqtSlot(dict)
    def modify_calculations_data_slot(self, params: dict):
        logger.debug(f"В modify_calculations_data_slot пришли данные {params}")
        path_keys = params.get("path_keys")
        operation = params.get("operation")

        if not path_keys or not isinstance(path_keys, list):
            logger.error("Некорректный или пустой список path_keys")
            return

        operations = {
            "add_reaction": self.process_add_reaction,
            "remove_reaction": self.process_remove_reaction,
            "highlight_reaction": self.process_highlight_reaction,
            "update_value": self.process_update_value
        }

        if operation in operations:
            operations[operation](path_keys, params)
        else:
            logger.warning("Неизвестная или отсутствующая операция над данными.")

    def plot_reaction_curve(self, file_name, reaction_name, bound_label, params):
        x_min, x_max = params[0]
        x = np.linspace(x_min, x_max, 100)
        y = self.calculate_reaction(params)
        curve_name = f"{reaction_name}_{bound_label}"
        self.plot_reaction.emit((file_name, curve_name), [x, y])

    def process_add_reaction(self, path_keys: list, _params: dict):
        file_name, reaction_name = path_keys
        if not self.file_data.check_operation_executed(file_name, "differential"):
            console.log("Данные нужно привести к da/dT")
            self.add_reaction_fail.emit()
            return

        df = self.file_data.dataframe_copies[file_name]
        data = cft.generate_default_function_data(df)
        self.calculations_data.set_value(path_keys.copy(), data)
        reaction_params = self.extract_reaction_params(path_keys)

        for bound_label, params in reaction_params.items():
            self.plot_reaction_curve(file_name, reaction_name, bound_label, params)

    def process_remove_reaction(self, path_keys: list, _params: dict):
        if len(path_keys) < 2:
            logger.error("Недостаточно информации в path_keys для удаления реакции")
            return
        file_name, reaction_name = path_keys
        if self.calculations_data.exists(path_keys):
            self.calculations_data.remove_value(path_keys)
            logger.debug(f"Удалена реакция {reaction_name} для файла {file_name}")
            console.log(f"Реакция {reaction_name} была успешно удалена")
        else:
            logger.warning(f"Реакция {reaction_name} не найдена в данных")
            console.log(f"Не удалось найти реакцию {reaction_name} для удаления")

    def process_highlight_reaction(self, path_keys: list, _params: dict):
        file_name = path_keys[0]
        self.file_data.plot_dataframe_signal.emit(self.file_data.dataframe_copies[file_name])
        data = self.calculations_data.get_value([file_name])
        reactions = data.keys()

        cumulative_y = {
            "upper_bound_coeffs": np.array([]),
            "lower_bound_coeffs": np.array([]),
            "coeffs": np.array([]),
        }
        x = None

        for reaction_name in reactions:
            reaction_params = self.extract_reaction_params([file_name, reaction_name])
            for bound_label, params in reaction_params.items():
                if bound_label in cumulative_y:
                    y = self.calculate_reaction(reaction_params.get(bound_label, []))
                    if x is None:
                        x_min, x_max = params[0]
                        x = np.linspace(x_min, x_max, 100)
                    cumulative_y[bound_label] = cumulative_y[bound_label] + y if cumulative_y[bound_label].size else y

            if reaction_name in path_keys:
                self.reaction_params_to_gui.emit(reaction_params)
                self.plot_reaction_curve(
                    file_name, reaction_name, "upper_bound_coeffs", reaction_params.get("upper_bound_coeffs", []))
                self.plot_reaction_curve(
                    file_name, reaction_name, "lower_bound_coeffs", reaction_params.get("lower_bound_coeffs", []))
            else:
                self.plot_reaction_curve(file_name, reaction_name, "coeffs", reaction_params.get("coeffs", []))

        for bound_label, y in cumulative_y.items():
            self.plot_reaction.emit((file_name, f'cumulative_{bound_label}'), [x, y])

    def process_update_value(self, path_keys: list, params: dict):
        try:
            new_value = params.get('value')
            if self.calculations_data.exists(path_keys):
                self.calculations_data.set_value(path_keys.copy(), new_value)
                self.process_highlight_reaction(path_keys[:2], params)
                logger.info(f"Данные по пути: {path_keys} изменены на: {new_value}")
            else:
                logger.error(f"Все данные: {self.calculations_data._data}")
                logger.error(f"Данных по пути: {path_keys} не найдено.")
        except Exception as e:
            logger.error(f"Непредусмотренная ошибка при обновлении данных по пути: {path_keys}: {str(e)}")
