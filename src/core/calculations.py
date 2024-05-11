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
    plot_reaction_signal = pyqtSignal(str, list)

    def __init__(self, file_data: FileData, calculations_data: CalculationsData):
        super().__init__()
        self.file_data = file_data
        self.calculations_data = calculations_data

    def generate_default_gaussian_data(self, file_name):
        df = self.file_data.dataframe_copies[file_name]
        x = df['temperature'].copy()
        y_columns = [col for col in df.columns if col != 'temperature']
        if y_columns:
            y = df[y_columns[0]]
            h = 0.8 * y.max()
            z = x.mean()
            w = 0.1 * (x.max() - x.min())

            h_lower = h * 0.9
            h_upper = h * 1.1
            w_lower = w * 0.9
            w_upper = w * 1.1

            result_dict = {
                "function": "gauss",
                "x": x.to_numpy(),
                "coeffs": {
                    "h": h,
                    "z": z,
                    "w": w
                },
                "upper_bound_coeffs": {
                    "h": h_upper,
                    "z": z,
                    "w": w_upper
                },
                "lower_bound_coeffs": {
                    "h": h_lower,
                    "z": z,
                    "w": w_lower
                }
            }
            return result_dict
        return {}

    def extract_reaction_params(self, path_keys: list):
        reaction_params = self.calculations_data.get_value(path_keys)
        x = reaction_params.get('x')
        function_type = reaction_params.get('function')
        coeffs = reaction_params.get('coeffs', {})
        upper_coeffs = reaction_params.get('upper_bound_coeffs', {})
        lower_coeffs = reaction_params.get('lower_bound_coeffs', {})

        x_range = (np.min(x), np.max(x))
        coeffs_tuple = (coeffs.get('h'), coeffs.get('z'), coeffs.get('w'))
        upper_coeffs_tuple = (upper_coeffs.get('h'), upper_coeffs.get('z'), upper_coeffs.get('w'))
        lower_coeffs_tuple = (lower_coeffs.get('h'), lower_coeffs.get('z'), lower_coeffs.get('w'))

        return {
            'value': (x_range, function_type, coeffs_tuple),
            'upper_bound': (x_range, function_type, upper_coeffs_tuple),
            'lower_bound': (x_range, function_type, lower_coeffs_tuple)
        }

    @lru_cache(maxsize=128)
    def calculate_reaction(self, reaction_params: tuple):
        x_range, function_type, coeffs = reaction_params
        x = np.linspace(x_range[0], x_range[1], 100)
        result = None
        if function_type == 'gauss':
            result = cft.gaussian(x, *coeffs)
        elif function_type == 'fraser':
            result = cft.fraser_suzuki(x, *coeffs)
        elif function_type == 'ads':
            result = cft.asymmetric_double_sigmoid(x, *coeffs)
        return result

    def diff_function(self, data: pd.DataFrame):
        return data.diff() * -1

    @pyqtSlot(dict)
    def modify_active_file_slot(self, params: dict):
        logger.debug(f'В modify_active_file_slot пришли данные {params}')
        operation = params.get('operation')
        file_name = params.get('file_name')
        if operation == "differential":
            if not self.file_data.check_operation_executed(file_name, operation):
                self.file_data.modify_data(self.diff_function, params)
            else:
                console.log('Данные уже приведены к da/dT')
        elif operation == "cancel_changes":
            self.file_data.reset_dataframe_copy(file_name)

    @pyqtSlot(dict)
    def modify_calculations_data_slot(self, params: dict):
        logger.debug(f'В modify_calculations_data_slot пришли данные {params}')
        path_keys = params.get('path_keys')
        operation = params.get('operation')

        if not path_keys or not isinstance(path_keys, list):
            logger.error("Некорректный или пустой список path_keys")
            return

        operations = {
            'add_reaction': self.process_add_reaction,
            'highlight_reaction': self.process_highlight_reaction
        }

        if operation in operations:
            operations[operation](path_keys, params)
        else:
            logger.warning("Неизвестная или отсутствующая операция над данными.")

    def process_add_reaction(self, path_keys: list, _params: dict):
        file_name = path_keys[0]
        data = self.generate_default_gaussian_data(file_name)
        self.calculations_data.set_value(path_keys.copy(), data)
        reaction_params = self.extract_reaction_params(path_keys)
        reaction_results = {key: self.calculate_reaction(params) for key, params in reaction_params.items()}
        for label, y in reaction_results.items():
            x_range = reaction_params[label][0]
            x = np.linspace(x_range[0], x_range[1], 100)
            self.plot_reaction_signal.emit(label, [x, y])

    def process_highlight_reaction(self, path_keys: list, _params: dict):
        file_name = path_keys[0]
        self.file_data.plot_dataframe_signal.emit(self.file_data.dataframe_copies[file_name])
        data = self.calculations_data.get_value([file_name])
        reactions = data.keys()
        for reaction in reactions:
            reaction_params = self.extract_reaction_params([file_name, reaction])
            if reaction in path_keys:
                reaction_results = {key: self.calculate_reaction(params) for key, params in reaction_params.items()}
                for label, y in reaction_results.items():
                    x_range = reaction_params[label][0]
                    x = np.linspace(x_range[0], x_range[1], 100)
                    self.plot_reaction_signal.emit(label, [x, y])
            else:
                value_x_range = reaction_params['value'][0]
                value_x = np.linspace(value_x_range[0], value_x_range[1], 100)
                value_y = self.calculate_reaction(reaction_params['value'])
                self.plot_reaction_signal.emit('value', [value_x, value_y])
        logger.debug(f'Реакции активного файла: {data.keys()}, имя файла: {file_name}, ключи запроса:{path_keys}')
