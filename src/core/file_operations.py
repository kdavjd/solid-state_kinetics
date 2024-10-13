import pandas as pd
from core.logger_config import logger
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot


class ActiveFileOperations(QObject):
    active_file_operations_signal = pyqtSignal(dict)

    def __init__(self):
        super().__init__()

    @pyqtSlot(dict)
    def modify_active_file(self, params: dict):
        logger.debug(f"В modify_active_file пришли данные {params}")
        operation = params.get("operation")

        if operation == "differential":
            params["function"] = self.diff_function

        params["actor"] = "active_file_operations"
        params["target"] = "file_data"
        self.active_file_operations_signal.emit(params)

    def diff_function(self, data: pd.DataFrame):
        return data.diff() * -1
