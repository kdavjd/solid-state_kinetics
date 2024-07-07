import json
from functools import reduce

from PyQt6.QtCore import QObject, pyqtSignal

from core.logger_config import logger


class CalculationsData(QObject):
    dataChanged = pyqtSignal(dict)

    def __init__(self, filename=None, parent=None):
        super().__init__(parent)
        self._filename = filename
        self._data = {}

    def load_data(self, data):
        self._data = data
        print(f"Загруженные данные: {self._data}")
        return self._data

    def save_data(self, export_data, filename=None):
        self._data = export_data
        print(f"Сохранённые данные: {self._data}")

        if filename:
            self._filename = filename

        try:
            with open(self._filename, 'w', encoding='utf-8') as file:
                json.dump(self._data, file, indent=4)
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
