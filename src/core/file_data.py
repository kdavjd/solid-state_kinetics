import os
from functools import wraps

import chardet
import pandas as pd
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

from core.logger_config import logger


def detect_encoding(func):
    def wrapper(self, *args, **kwargs):
        with open(self.file_path, 'rb') as f:
            result = chardet.detect(f.read(100_000))
        kwargs['encoding'] = result['encoding']
        return func(self, *args, **kwargs)
    return wrapper


def detect_decimal(func):
    @wraps(func)
    def wrapper(self, **kwargs):
        encoding = kwargs.get('encoding', 'utf-8')
        with open(self.file_path, 'r', encoding=encoding) as f:
            sample_lines = [next(f) for _ in range(100)]
        sample_text = ''.join(sample_lines)
        # Простая эвристика: если запятых больше, чем точек, предполагаем,
        # что запятая используется как десятичный разделитель
        decimal_sep = ',' if sample_text.count(
            ',') > sample_text.count('.') else '.'
        kwargs['decimal'] = decimal_sep
        return func(self, **kwargs)
    return wrapper


class FileData(QObject):
    data_loaded_signal = pyqtSignal(pd.DataFrame)

    def __init__(self):
        super().__init__()
        self.data = None
        self.file_path = None
        self.delimiter = ','
        self.skip_rows = 0
        self.columns_names = None

    @pyqtSlot(tuple)
    def load_file(self, file_info):
        self.file_path, self.delimiter, self.skip_rows, columns_names_str = file_info
        self.columns_names = columns_names_str.split(
            ',') if columns_names_str else None
        _, file_extension = os.path.splitext(self.file_path)
        if file_extension == '.csv':
            self.load_csv()
        elif file_extension == '.txt':
            self.load_txt()

    @detect_encoding
    @detect_decimal
    def load_csv(self, **kwargs):
        try:
            self.data = pd.read_csv(
                self.file_path, sep=self.delimiter, engine='python',
                on_bad_lines='skip', skiprows=self.skip_rows, **kwargs)
            self.fetch_data()
        except Exception as e:
            logger.error("Ошибка при загрузке CSV файла: %s", e)

    @detect_encoding
    @detect_decimal
    def load_txt(self, **kwargs):
        try:
            self.data = pd.read_table(
                self.file_path, sep=self.delimiter, skiprows=self.skip_rows, **kwargs)
            self.fetch_data()
        except Exception as e:
            logger.error("Ошибка при загрузке TXT файла: %s", e)

    def fetch_data(self):
        if self.columns_names and len(self.columns_names) == len(self.data.columns):
            self.data.columns = [name.strip() for name in self.columns_names]
            logger.debug("Имена столбцов успешно обновлены.")
        else:
            logger.warning(
                "Количество имен столбцов не соответствует количеству столбцов в данных.")

        self.data_loaded_signal.emit(self.data)
