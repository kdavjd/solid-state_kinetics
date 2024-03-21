import pandas as pd
from PyQt6.QtCore import QAbstractTableModel, QModelIndex, Qt, pyqtSignal

from core.logger_config import logger


class PandasModel(QAbstractTableModel):
    """
    Класс для взаимодействия между pandas DataFrame и QTableView.

    Attributes:
        data_changed_signal (pyqtSignal): Сигнал изменения данных.
    """

    data_changed_signal = pyqtSignal(pd.DataFrame)

    def __init__(self, data, parent=None):
        """
        Инициализация класса.

        Args:
            data (DataFrame): pandas DataFrame для отображения.
            parent (QWidget, optional): родительский виджет.
        """
        QAbstractTableModel.__init__(self, parent)
        self._data = data

    def rowCount(self, parent=None):
        """
        Возвращает количество строк в DataFrame.

        Args:
            parent (QModelIndex, optional): родительский индекс (не используется).

        Returns:
            int: число строк.
        """
        return self._data.shape[0]

    def columnCount(self, parent=None):
        """
        Возвращает количество столбцов в DataFrame.

        Args:
            parent (QModelIndex, optional): родительский индекс (не используется).

        Returns:
            int: число столбцов.
        """
        return self._data.shape[1]

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        """
        Возвращает данные для отображения в таблице.

        Args:
            index (QModelIndex): индекс ячейки.
            role (Qt.ItemDataRole, optional): роль данных.

        Returns:
            QVariant: данные для отображения или None, если ячейка недействительна.
        """
        if index.isValid():
            if role == Qt.ItemDataRole.DisplayRole:
                return str(self._data.iloc[index.row(), index.column()])
        return None

    def removeRow(self, row, parent=None):
        """
        Удаляет строку из DataFrame.

        Args:
            row (int): номер строки для удаления.
            parent (QModelIndex, optional): родительский индекс (не используется).

        Returns:
            bool: True, если строка успешно удалена, иначе False.
        """
        # Используем QModelIndex(), чтобы указать отсутствие родителя
        self.beginRemoveRows(QModelIndex(), row, row)
        try:
            self._data = self._data.drop(self._data.index[row])
            self.endRemoveRows()
            self.data_changed_signal.emit(self._data)
            return True
        except Exception as e:
            logger.error(f"Ошибка при удалении строки: {e}")
            self.endRemoveRows()
            return False

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        """
        Возвращает данные заголовка.

        Args:
            section (int): номер раздела (столбца или строки).
            orientation (Qt.Orientation): ориентация заголовка (горизонтальная или вертикальная).
            role (Qt.ItemDataRole, optional): роль данных.

        Returns:
            QVariant: данные заголовка или None, если данные недоступны.
        """
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            return self._data.columns[section]
        if orientation == Qt.Orientation.Vertical:
            return self._data.index[section]

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        """
        Изменяет данные в DataFrame.

        Args:
            index (QModelIndex): индекс ячейки.
            value (QVariant): новое значение.
            role (Qt.ItemDataRole, optional): роль данных.

        Returns:
            bool: True, если данные успешно изменены, иначе False.
        """
        if not index.isValid() or role != Qt.ItemDataRole.EditRole:
            return False

        row = index.row()
        col = index.column()

        try:
            converted_value = float(str(value).replace(',', '.'))
            self._data.iat[row, col] = converted_value
            self.dataChanged.emit(index, index, [role])
            self.data_changed_signal.emit(self._data)
            logger.debug(f"Данные изменены в строке {
                         row}, столбце {col}: {converted_value}")
            return True
        except Exception as e:
            print(f"Error setting data: {e}")
            return False

    def flags(self, index):
        """
        Определяет возможности ячейки.

        Args:
            index (QModelIndex): индекс ячейки.

        Returns:
            Qt.ItemFlags: флаги, определяющие возможности ячейки.
        """
        return Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
