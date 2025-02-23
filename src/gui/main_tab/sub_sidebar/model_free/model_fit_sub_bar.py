from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.core.app_settings import MODEL_FIT_METHODS, NUC_MODELS_LIST


class ModelFitSubBar(QWidget):
    create_series_signal = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.layout = QVBoxLayout(self)

        self.model_combobox = QComboBox(self)
        self.model_combobox.addItems(MODEL_FIT_METHODS)
        self.layout.addWidget(self.model_combobox)

        self.form_layout = QFormLayout()
        self.alpha_min_input = QLineEdit(self)
        self.alpha_min_input.setText("0.005")
        self.alpha_min_input.setToolTip("alpha_min - minimum conversion value for calculation")
        self.form_layout.addRow("α_min:", self.alpha_min_input)

        self.alpha_max_input = QLineEdit(self)
        self.alpha_max_input.setText("0.995")
        self.alpha_max_input.setToolTip("alpha_max - maximum conversion value for calculation")
        self.form_layout.addRow("α_max:", self.alpha_max_input)

        self.valid_proportion_input = QLineEdit(self)
        self.valid_proportion_input.setText("0.8")
        self.valid_proportion_input.setToolTip(
            "valid proportion - the proportion of values in the model calculation that is not infinity or NaN.\
                If it is smaller, the model is ignored."
        )
        self.form_layout.addRow("valid proportion:", self.valid_proportion_input)

        self.layout.addLayout(self.form_layout)

        # Calculate button
        self.calculate_button = QPushButton("Calculate", self)
        self.calculate_button.clicked.connect(self.on_calculate_clicked)
        self.layout.addWidget(self.calculate_button)

        # Table for results
        self.results_table = QTableWidget(self)
        self.results_table.setColumnCount(4)
        self.results_table.setHorizontalHeaderLabels(["Model", "R2_score", "Ea", "A"])
        self.layout.addWidget(self.results_table)

        # Drop-down for NUC models list and plot button
        self.plot_layout = QHBoxLayout()
        self.nuc_combobox = QComboBox(self)
        self.nuc_combobox.addItems(NUC_MODELS_LIST)
        self.plot_button = QPushButton("Plot result", self)
        self.plot_layout.addWidget(self.nuc_combobox)
        self.plot_layout.addWidget(self.plot_button)
        self.layout.addLayout(self.plot_layout)

        self.setLayout(self.layout)

    def on_calculate_clicked(self):
        # Validate inputs
        try:
            alpha_min = float(self.alpha_min_input.text())
            alpha_max = float(self.alpha_max_input.text())
            valid_proportion = float(self.valid_proportion_input.text())

            # Validate alpha_min and alpha_max
            if not (0 <= alpha_min <= 0.999):
                raise ValueError("alpha_min must be between 0 and 0.999")
            if not (0 <= alpha_max <= 1):
                raise ValueError("alpha_max must be between 0 and 1")
            if alpha_min > alpha_max:
                raise ValueError("alpha_min cannot be greater than alpha_max")

            # Validate valid_proportion
            if not (0.001 <= valid_proportion <= 1):
                raise ValueError("valid proportion must be between 0.001 and 1")

            # If validation passes, you can perform further calculations or processing here
            self.populate_table()

        except ValueError as e:
            QMessageBox.warning(self, "Input Error", str(e))

    def populate_table(self):
        # Clear existing rows
        self.results_table.setRowCount(0)

        # Example of adding some rows to the table
        data = [
            ("Model A", 0.85, 0.78, 1.23),
            ("Model B", 0.90, 0.82, 1.18),
            ("Model C", 0.88, 0.80, 1.25),
        ]
        for row_data in data:
            row_position = self.results_table.rowCount()
            self.results_table.insertRow(row_position)
            for col, value in enumerate(row_data):
                self.results_table.setItem(row_position, col, QTableWidgetItem(str(value)))
