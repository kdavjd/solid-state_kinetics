import json
from functools import reduce

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

    def check_all_stages_have_data(self):
        for experiment, details in self.data.items():
            if any(stage_data is None for stage_data in details.get('stages', {}).values()):
                return False
        return True

    def get_stage_data(self, keys):
        return reduce(lambda acc, key: (acc or {}).get(key), keys, self.data)
