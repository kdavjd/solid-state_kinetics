import pandas as pd
from numpy import ndarray
from PyQt6.QtCore import QObject, pyqtSlot

from core.logger_config import logger


class Calculations(QObject):
    def __init__(self, file_data=None, calculations_data=None):
        super().__init__()
        self.file_data = file_data
        self.calculations_data = calculations_data

    def diff_function(self, data: pd.DataFrame):
        return data.diff() * -1

    @pyqtSlot(str, str)
    def modify_active_file_slot(self, command, file_name):
        if command == "Привести к da/dT":
            self.file_data.modify_data(self.diff_function, file_name)
        elif command == "Отменить изменения":
            self.file_data.reset_dataframe_copy(file_name)

    @pyqtSlot(list, str, ndarray)
    def modify_calculations_data_slot(self, *args):
        logger.debug(f'В modify_calculations_data_slot пришли данные {args}')
