import pandas as pd
from numpy import ndarray
from PyQt6.QtCore import QObject, pyqtSlot

from core.logger_config import logger
from core.logger_console import LoggerConsole as console


class Calculations(QObject):
    def __init__(self, file_data=None, calculations_data=None):
        super().__init__()
        self.file_data = file_data
        self.calculations_data = calculations_data

    def diff_function(self, data: pd.DataFrame):
        return data.diff() * -1

    @pyqtSlot(dict)
    def modify_active_file_slot(self, params: dict):
        operation = params.get('операция')
        file_name = params.get('файл')
        if operation == "Привести к da/dT":
            if not self.file_data.check_operation_executed(file_name, operation):
                self.file_data.modify_data(self.diff_function, params)
            else:
                console.log('Данные уже приведены к da/dT')
        elif operation == "Отменить изменения":
            self.file_data.reset_dataframe_copy(file_name)

    @pyqtSlot(list, str, ndarray)
    def modify_calculations_data_slot(self, *args):
        logger.debug(f'В modify_calculations_data_slot пришли данные {args}')
