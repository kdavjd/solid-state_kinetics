import json
from functools import reduce
from typing import Any, Dict, List

import numpy as np
from core.base_signals import BaseSlots
from PyQt6.QtCore import pyqtSignal

from src.core.app_settings import OperationType
from src.core.logger_config import logger
from src.core.logger_console import LoggerConsole as console


class CalculationsData(BaseSlots):
    dataChanged = pyqtSignal(dict)

    def __init__(self, signals):
        super().__init__(actor_name="calculations_data", signals=signals)
        self._data: Dict[str, Any] = {}
        self._filename: str = ""

    def load_reactions(self, load_file_name: str, file_name: str) -> Dict[str, Any]:
        """Load reaction data from a file.

        Args:
            load_file_name (str): The file to load data from.
            file_name (str): The key name under which data will be stored.

        Returns:
            Dict[str, Any]: The loaded data if successful, otherwise an empty dict.
        """
        try:
            with open(load_file_name, "r", encoding="utf-8") as file:
                data = json.load(file)

            for reaction_key, reaction_data in data.items():
                if "x" in reaction_data:
                    reaction_data["x"] = np.array(reaction_data["x"])

            self.set_value([file_name], data)
            console.log(f"Data successfully imported from file:\n\n{load_file_name}")
            return data
        except IOError as e:
            logger.error(f"{e}")
            return {}

    def save_data(self) -> None:
        """Save the current data to a file."""
        try:
            with open(self._filename, "w") as file:
                json.dump(self._data, file, indent=4)
        except IOError as e:
            logger.error(f"{e}")

    def get_value(self, keys: List[str]) -> Dict[str, Any]:
        """Get a nested value from the data dictionary.

        Args:
            keys (List[str]): The list of keys representing the nested path.

        Returns:
            Dict[str, Any]: The retrieved data or an empty dict if not found.
        """
        return reduce(lambda data, key: data.get(key, {}), keys, self._data)

    def set_value(self, keys: List[str], value: Any) -> None:
        """Set a nested value in the data dictionary.

        Args:
            keys (List[str]): The list of keys to define the nested path.
            value (Any): The value to set.
        """
        if not keys:
            return
        last_key = keys.pop()
        nested_dict = reduce(lambda data, key: data.setdefault(key, {}), keys, self._data)
        nested_dict[last_key] = value

    def exists(self, keys: List[str]) -> bool:
        """Check if a nested key path exists in the data.

        Args:
            keys (List[str]): The list of keys representing the nested path.

        Returns:
            bool: True if the path exists, False otherwise.
        """
        try:
            _ = reduce(lambda data, key: data[key], keys, self._data)
            return True
        except KeyError:
            return False

    def remove_value(self, keys: List[str]) -> None:
        """Remove a nested value from the data dictionary.

        Args:
            keys (List[str]): The list of keys representing the nested path to remove.
        """
        if not keys:
            return
        if self.exists(keys):
            last_key = keys.pop()
            parent_dict = reduce(lambda data, key: data.get(key, {}), keys, self._data)
            if last_key in parent_dict:
                del parent_dict[last_key]
                logger.debug({"operation": "remove_reaction", "keys": keys + [last_key]})

    def process_request(self, params: dict) -> None:
        """Process incoming requests related to data operations.

        Args:
            params (dict): The request parameters, must contain 'operation' and possibly 'path_keys', 'value', etc.
        """
        operation = params.get("operation")
        actor = params.get("actor")
        logger.debug(f"{self.actor_name} processing request '{operation}' from '{actor}'")

        if operation == OperationType.GET_VALUE:
            path_keys = params.get("path_keys", [])
            if not isinstance(path_keys, list) or any(not isinstance(k, str) for k in path_keys):
                logger.error("Invalid path_keys provided for get_value.")
                params["data"] = {}
            else:
                params["data"] = self.get_value(path_keys)

        elif operation == OperationType.SET_VALUE:
            path_keys = params.get("path_keys", [])
            value = params.get("value")
            if not isinstance(path_keys, list) or any(not isinstance(k, str) for k in path_keys):
                logger.error("Invalid path_keys provided for set_value.")
                params["data"] = False
            else:
                self.set_value(path_keys, value)
                params["data"] = True

        elif operation == OperationType.REMOVE_VALUE:
            path_keys = params.get("path_keys", [])
            if not isinstance(path_keys, list) or any(not isinstance(k, str) for k in path_keys):
                logger.error("Invalid path_keys provided for remove_value.")
                params["data"] = False
            else:
                self.remove_value(path_keys)
                params["data"] = True

        elif operation == OperationType.IMPORT_REACTIONS:
            load_file_name = params.get("import_file_name")
            file_name = params.get("file_name")
            if isinstance(load_file_name, str) and isinstance(file_name, str):
                params["data"] = self.load_reactions(load_file_name, file_name)
            else:
                logger.error("Invalid import file name or target file name provided.")
                params["data"] = None

        elif operation == OperationType.GET_FULL_DATA:
            params["data"] = self._data.copy()

        else:
            logger.debug(f"Unknown operation: {operation}")
            params["data"] = None

        response = {
            "actor": self.actor_name,
            "target": actor,
            "operation": operation,
            "request_id": params["request_id"],
            "data": params["data"],
        }
        self.signals.response_signal.emit(response)
