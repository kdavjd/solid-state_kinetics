import json
from functools import reduce

from core.logger_config import logger
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot


class CalculationsData(QObject):
    dataChanged = pyqtSignal(dict)
    response_signal = pyqtSignal(dict)

    def __init__(self, filename=None, parent=None):
        super().__init__(parent)
        self._filename = filename
        self._data = {}
        if filename:
            self.load_data()

    def load_data(self):
        try:
            with open(self._filename, "r") as file:
                self.data = json.load(file)
        except IOError as e:
            print(f"Ошибка загрузки данных: {e}")

    def save_data(self):
        try:
            with open(self._filename, "w") as file:
                json.dump(self.data, file, indent=4)
        except IOError as e:
            print(f"Ошибка сохранения данных: {e}")

    def get_value(self, keys: list[str]) -> dict:
        return reduce(lambda data, key: data.get(key, {}), keys, self._data)

    def set_value(self, keys: list[str], value):
        last_key = keys.pop()
        nested_dict = reduce(lambda data, key: data.setdefault(key, {}), keys, self._data)
        nested_dict[last_key] = value

    def exists(self, keys: list[str]) -> bool:
        try:
            return reduce(lambda data, key: data[key], keys, self._data) is not None
        except KeyError:
            return False

    def remove_value(self, keys: list[str]):
        if self.exists(keys):
            last_key = keys.pop()
            parent_dict = reduce(lambda data, key: data.get(key, {}), keys, self._data)
            if last_key in parent_dict:
                del parent_dict[last_key]
                logger.debug({"operation": "remove_reaction", "keys": keys + [last_key]})

    @pyqtSlot(dict)
    def request_slot(self, params: dict):
        if params["target"] != "calculations_data":
            return

        operation, path_keys, value = params.get("operation"), params.get("path_keys", None), params.get("value", None)
        logger.debug(f"В calculations_data_slot пришел запрос {operation} от {params['actor']}")

        if operation == "get_value":
            params["data"] = self.get_value(path_keys)
        elif operation == "set_value":
            params["data"] = True if self.exists(path_keys) else False
            self.set_value(path_keys, value)
        elif operation == "remove_value":
            params["data"] = True if self.exists(path_keys) else False
            self.remove_value(path_keys)
        elif operation == "get_full_data":
            params["data"] = self._data
        else:
            params["data"] = None

        params["target"], params["actor"] = params["actor"], params["target"]
        self.response_signal.emit(params)
