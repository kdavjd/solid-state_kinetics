import numpy as np
import pandas as pd
from PyQt6.QtCore import QObject, pyqtSlot

from core.logger_config import logger
from core.logger_console import LoggerConsole as console


class Calculations(QObject):
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
