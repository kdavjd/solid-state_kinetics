import json
from functools import reduce

from core.logger_config import logger
from PyQt6.QtCore import QObject, pyqtSignal


class CalculationsData(QObject):
    dataChanged = pyqtSignal(dict)

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
