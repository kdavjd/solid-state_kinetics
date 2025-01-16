import pandas as pd
from core.base_signals import BaseSlots

from src.core.logger_config import logger


class ActiveFileOperations(BaseSlots):
    def __init__(self, signals):
        super().__init__(actor_name="active_file_operations", signals=signals)

    def process_request(self, params: dict):
        operation = params.get("operation")
        actor = params.get("actor")
        logger.debug(f"{self.actor_name} processing request '{operation}' from '{actor}'")
        response = params.copy()

        if operation == "differential":
            response["data"] = self.diff_function
        if operation == "load":
            pass
        else:
            logger.warning(f"{self.actor_name} received unknown operation '{operation}'")

        response["target"], response["actor"] = response["actor"], response["target"]
        self.signals.response_signal.emit(response)

    def diff_function(self, data: pd.DataFrame):
        return data.diff() * -1
