import pandas as pd
from PyQt6.QtCore import QObject, pyqtSlot


class Calcultaions(QObject):
    def __init__(self, file_data=None, calculations_data=None):
        super().__init__()
        self.file_data = file_data
        self.calculations_data = calculations_data

    def diff_function(self, data: pd.DataFrame):
        return data.diff() * -1

    @pyqtSlot(str, str)
    def handle_modify_signal(self, command, key):
        if command == "Привести к da/dT":
            self.file_data.modify_data(self.diff_function, key)
        elif command == "Отменить изменения":
            self.file_data.reset_dataframe_copy(key)
