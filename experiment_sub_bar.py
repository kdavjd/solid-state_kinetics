from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from scipy.signal import savgol_filter
import logging

logger = logging.getLogger(__name__)


class SmoothingBlock(QWidget):
    """
    A QWidget subclass that provides UI components for selecting and configuring
    the smoothing method applied to data.
    """
    smoothed_data_ready = pyqtSignal(list)  # Signal to emit smoothed data

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayout(QVBoxLayout())
        self.current_data = []  # Store data for smoothing
        self.setup_ui()

    def setup_ui(self):
        # Initialize smoothing method selection
        self.smoothing_method = QComboBox()
        self.smoothing_method.addItems(["Savitzky-Golay", "Other"])
        logger.debug("Initialized smoothing_method ComboBox with items.")

        # Initialize window size and polynomial order inputs
        self.n_window = QLineEdit("11")  # Default window size
        self.n_poly = QLineEdit("3")    # Default polynomial order
        logger.debug("Initialized n_window and n_poly QLineEdits with default values.")

        # Initialize apply button
        self.apply_button = QPushButton("Apply")
        logger.debug("Initialized apply_button with label 'Apply'.")

        # Layout for UI
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Smoothing method:"))
        layout.addWidget(self.smoothing_method)

        # Window size and polynomial order
        layout_window = QVBoxLayout()
        layout_window.addWidget(QLabel("Window size:"))
        layout_window.addWidget(self.n_window)

        layout_poly = QVBoxLayout()
        layout_poly.addWidget(QLabel("Polynomial order:"))
        layout_poly.addWidget(self.n_poly)

        h_layout = QHBoxLayout()
        h_layout.addLayout(layout_window)
        h_layout.addLayout(layout_poly)
        layout.addLayout(h_layout)

        layout.addWidget(self.apply_button)
        self.layout().addLayout(layout)
        logger.debug("SmoothingBlock UI initialized successfully.")

        # Connect button
        self.apply_button.clicked.connect(self.handle_apply_smoothing)

    def load_data(self, data: list[float]):
        logger.info(f"Data received for loading: {data}")
        self.current_data = data
        logger.info("Data loaded into SmoothingBlock.")

    def handle_apply_smoothing(self):

        if not self.current_data:
            logger.warning("No data loaded for smoothing.")
            QMessageBox.warning(self, "Warning", "No data loaded for smoothing.")
            return

        smoothed_data = self.apply_smoothing(self.current_data)
        logger.info(f"Smoothed data: {smoothed_data}")
        self.smoothed_data_ready.emit(smoothed_data)

    def apply_smoothing(self, data: list[float]) -> list[float]:

        try:
            window_length = int(self.n_window.text())
            poly_order = int(self.n_poly.text())

            if window_length % 2 == 0:
                raise ValueError("Window size must be an odd number.")
            if window_length <= 0 or poly_order < 0:
                raise ValueError("Window size must be positive and polynomial order must be non-negative.")
            if len(data) < window_length:
                raise ValueError("Data length must be greater than or equal to the window size.")

            smoothed_data = savgol_filter(data, window_length=window_length, polyorder=poly_order)
            logger.info(f"Applied Savitzky-Golay smoothing with window_length={window_length}, poly_order={poly_order}")
            return smoothed_data.tolist()

        except Exception as e:
            logger.error(f"Error during smoothing: {e}")
            QMessageBox.critical(self, "Smoothing Error", f"Error: {str(e)}")
            return data


class BackgroundSubtractionBlock(QWidget):
    """
    A QWidget subclass for configuring background subtraction.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayout(QVBoxLayout())

        self.background_method = QComboBox()
        self.background_method.addItems([
            "Linear", "Sigmoidal", "Tangential", "Left Tangential",
            "Left Sigmoidal", "Right Tangential", "Right Sigmoidal", "Bezier",
        ])
        logger.debug("Initialized background_method ComboBox with items.")

        self.range_left = QLineEdit()
        self.range_right = QLineEdit()
        logger.debug("Initialized range_left and range_right QLineEdits.")

        self.apply_button = QPushButton("Apply")
        logger.debug("Initialized apply_button with label 'Apply'.")

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Background subtraction method:"))
        layout.addWidget(self.background_method)

        layout.addWidget(QLabel("Background subtraction range:"))

        layout_left = QVBoxLayout()
        layout_left.addWidget(QLabel("Left:"))
        layout_left.addWidget(self.range_left)

        layout_right = QVBoxLayout()
        layout_right.addWidget(QLabel("Right:"))
        layout_right.addWidget(self.range_right)

        h_layout = QHBoxLayout()
        h_layout.addLayout(layout_left)
        h_layout.addLayout(layout_right)
        layout.addLayout(h_layout)

        layout.addWidget(self.apply_button)
        self.layout().addLayout(layout)
        logger.debug("BackgroundSubtractionBlock UI initialized successfully.")


class ActionButtonsBlock(QWidget):
    """
    A QWidget subclass for action buttons.
    """
    cancel_changes_clicked = pyqtSignal(dict)
    derivative_clicked = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayout(QVBoxLayout())

        self.cancel_changes_button = QPushButton("Reset Changes")
        self.derivative_button = QPushButton("To da/dT")
        logger.debug("Initialized cancel_changes_button and derivative_button.")

        self.cancel_changes_button.clicked.connect(self.emit_cancel_changes_signal)
        self.derivative_button.clicked.connect(self.emit_derivative_signal)

        self.layout().addWidget(self.derivative_button)
        self.layout().addWidget(self.cancel_changes_button)

    def emit_cancel_changes_signal(self):
        logger.debug("Cancel Changes button clicked.")
        self.cancel_changes_clicked.emit({"operation": "reset_file_data"})

    def emit_derivative_signal(self):
        logger.debug("Derivative button clicked.")
        self.derivative_clicked.emit({"operation": "differential"})


class ExperimentSubBar(QWidget):
    """
    A QWidget subclass aggregating Smoothing, Background Subtraction, and Action Buttons blocks.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.smoothing_block = SmoothingBlock(self)
        self.background_subtraction_block = BackgroundSubtractionBlock(self)
        self.action_buttons_block = ActionButtonsBlock(self)

        layout.addWidget(self.smoothing_block)
        layout.addWidget(self.background_subtraction_block)
        layout.addWidget(self.action_buttons_block)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.parent():
            new_width = self.parent().width()
            self.setMaximumWidth(new_width)
