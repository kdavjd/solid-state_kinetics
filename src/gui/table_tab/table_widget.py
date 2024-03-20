import pandas as pd
from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem


class TableWidget(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.cell_width = 50
        self.cell_height = 20

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.horizontalHeader().setVisible(True)
        self.verticalHeader().setVisible(True)

        self.horizontalHeader().setDefaultSectionSize(self.cell_width)
        self.verticalHeader().setDefaultSectionSize(self.cell_height)

    @pyqtSlot(pd.DataFrame)
    def display_dataframe(self, df):
        self.clear()
        self.setRowCount(len(df.index))
        self.setColumnCount(len(df.columns))
        self.setHorizontalHeaderLabels(df.columns.tolist())

        for i, (index, row) in enumerate(df.iterrows()):
            for j, value in enumerate(row):
                self.setItem(i, j, QTableWidgetItem(str(value)))
