import pandas as pd

from src.core.basic_signals import BasicSignals
from src.core.logger_config import logger


class ActiveFileOperations(BasicSignals):
    def __init__(self, dispatcher):
        super().__init__(actor_name="active_file_operations", dispatcher=dispatcher)

    def process_request(self, params: dict):
        operation = params.get("operation")
        actor = params.get("actor")
        logger.debug(f"{self.actor_name} processing request '{operation}' from '{actor}'")
        response = params.copy()

        if operation == "differential":
            response["data"] = self.diff_function
        else:
            logger.warning(f"{self.actor_name} received unknown operation '{operation}'")

        response["target"], response["actor"] = response["actor"], response["target"]
        self.dispatcher.response_signal.emit(response)

    def diff_function(self, data: pd.DataFrame):
        return data.diff() * -1
