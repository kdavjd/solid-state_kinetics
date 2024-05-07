import numpy as np
import pandas as pd
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

from core.logger_config import logger
from core.logger_console import LoggerConsole as console


class Calculations(QObject):
    plot_df_signal = pyqtSignal(pd.DataFrame)

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
        x = df['temperature']
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

            gauss_values = self.gaussian(x, h, z, w)
            gauss_lower_values = self.gaussian(x, h_lower, z, w_lower)
            gauss_upper_values = self.gaussian(x, h_upper, z, w_upper)

            result_dict = {
                "function": "gauss",
                "x": x.to_numpy(),
                "y": {
                    "value": gauss_values,
                    "lower_bound": gauss_lower_values,
                    "upper_bound": gauss_upper_values
                },
                "w": {
                    "value": w,
                    "lower_bound": w_lower,
                    "upper_bound": w_upper
                },
                "h": {
                    "value": h,
                    "lower_bound": h_lower,
                    "upper_bound": h_upper
                },
                "z": {
                    "value": z,
                    "lower_bound": z - 0.1 * abs(z),
                    "upper_bound": z + 0.1 * abs(z)
                },
            }
            return result_dict
        return {}

    @staticmethod
    def create_data_frame(data):
        data_frame = pd.DataFrame({
            "temperature": data["x"],
            "value": data["y"]["value"],
            "lower_bound": data["y"]["lower_bound"],
            "upper_bound": data["y"]["upper_bound"]
        })
        return data_frame

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
                self.calculations_data.set_value(path_keys, data)
                df = self.create_data_frame(data)
                self.plot_df_signal.emit(df)
        else:
            logger.error("Некорректный или пустой список path_keys")
