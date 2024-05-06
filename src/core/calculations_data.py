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
        if filename:
            self.load_data()

    def load_data(self):
        try:
            with open(self._filename, 'r') as file:
                self.data = json.load(file)
        except IOError as e:
            print(f"Ошибка загрузки данных: {e}")

    def save_data(self):
        try:
            with open(self._filename, 'w') as file:
                json.dump(self.data, file, indent=4)
        except IOError as e:
            print(f"Ошибка сохранения данных: {e}")

    def get_value(self, keys: list[str]):
        return reduce(lambda data, key: (data or {}).get(key), keys, self._data)

    def set_value(self, keys: list[str], value):
        last_key = keys.pop()
        nested_dict = reduce(lambda data, key: data.setdefault(key, {}), keys, self._data)
        nested_dict[last_key] = value
        logger.debug(f'Данные вычислений: {self._data}')
