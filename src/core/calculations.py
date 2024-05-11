import numpy as np
import pandas as pd
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

from core.logger_config import logger
from core.logger_console import LoggerConsole as console


class Calculations(QObject):
    plot_reaction_signal = pyqtSignal(str, list)

    def __init__(self, file_data=None, calculations_data=None):
        super().__init__()
        self.file_data = file_data
        self.calculations_data = calculations_data

    @staticmethod
    def gaussian(x, h, z, w) -> np.ndarray:
        return h * np.exp(-((x - z) ** 2) / (2 * w ** 2))

    @staticmethod
    def fraser_suzuki(x, h, z, w, a3) -> np.ndarray:
        with np.errstate(divide='ignore', invalid='ignore'):
            result = h * np.exp(-np.log(2)*((np.log(1+2*a3*((x-z)/w))/a3)**2))
        result = np.nan_to_num(result, nan=0)
        return result

    @staticmethod
    def asymmetric_double_sigmoid(x, h, z, w, s1, s2) -> np.ndarray:
        safe_x = np.clip(x, -709, 709)
        exp_arg = -((safe_x - z + w/2) / s1)
        clipped_exp_arg = np.clip(exp_arg, -709, 709)
        term1 = 1 / (1 + np.exp(clipped_exp_arg))
        inner_term = 1 / (1 + np.exp(-((safe_x - z - w/2) / s2)))
        term2 = 1 - inner_term
        return h * term1 * term2

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
                    "w": w,
                    "h": h,
                    "z": z
                },
                "upper_bound_coeffs": {
                    "w": w_upper,
                    "h": h_upper,
                    "z": z
                },
                "lower_bound_coeffs": {
                    "w": w_lower,
                    "h": h_lower,
                    "z": z
                }
            }
            return result_dict
        return {}

    def extract_reaction_params(self, path_keys: list):
        reaction_params = self.calculations_data.get_value(path_keys)
        x = reaction_params.get('x')
        function_type = reaction_params.get('function')
        coeffs = reaction_params.get('coeffs', {})
        upper_bound_coeffs = reaction_params.get('upper_bound_coeffs', {})
        lower_bound_coeffs = reaction_params.get('lower_bound_coeffs', {})

        return {
            'value': (x, function_type, coeffs),
            'upper_bound': (x, function_type, upper_bound_coeffs),
            'lower_bound': (x, function_type, lower_bound_coeffs)
        }

    def calculate_reaction(self, reaction_params: tuple):
        x, function_type, coeffs = reaction_params
        result = None
        if function_type == 'gauss':
            result = self.gaussian(x, **coeffs)
        elif function_type == 'fraser':
            result = self.fraser_suzuki(x, **coeffs)
        elif function_type == 'ads':
            result = self.asymmetric_double_sigmoid(x, **coeffs)
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
        operation = params.get('operation')
        path_keys = params.get('path_keys')
        if path_keys and isinstance(path_keys, list):
            file_name = path_keys[0]
            if operation == 'add_reaction':
                data = self.generate_default_gaussian_data(file_name)
                self.calculations_data.set_value(path_keys.copy(), data)
                reaction_params = self.extract_reaction_params(path_keys)
                reaction_results = {key: self.calculate_reaction(params)
                                    for key, params in reaction_params.items()}
                for key, value in reaction_results.items():
                    self.plot_reaction_signal.emit(key, [reaction_params[key][0], value])

            elif operation == 'highlight_reaction':
                self.file_data.plot_dataframe_signal.emit(self.file_data.dataframe_copies[file_name])
                data = self.calculations_data.get_value([file_name])
                reactions = data.keys()
                for reaction in reactions:
                    reaction_params = self.extract_reaction_params([file_name, reaction])
                    if reaction in path_keys:
                        reaction_results = {key: self.calculate_reaction(params)
                                            for key, params in reaction_params.items()}
                        for key, value in reaction_results.items():
                            self.plot_reaction_signal.emit(key, [reaction_params[key][0], value])
                    else:
                        value = self.calculate_reaction(reaction_params['value'])
                        self.plot_reaction_signal.emit('value', [reaction_params['value'][0], value])
                logger.info(
                    f'Реакции активного файла: {data.keys()}, имя файла: {file_name},\
                        ключи запроса:{path_keys}')
            else:
                logger.warning("Неизвестная или отсуствующая операция над данными.")
        else:
            logger.error("Некорректный или пустой список path_keys")
