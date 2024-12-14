from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.core.logger_config import logger


class SmoothingBlock(QWidget):
    """
    A QWidget subclass that provides UI components for selecting and configuring
    the smoothing method applied to data.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayout(QVBoxLayout())

        # Initialize smoothing method selection
        self.smoothing_method = QComboBox()
        self.smoothing_method.addItems(["Savitzky-Golay", "Other"])
        logger.debug("Initialized smoothing_method ComboBox with items.")

        # Initialize window size and polynomial order inputs
        self.n_window = QLineEdit("1")
        self.n_poly = QLineEdit("0")
        logger.debug("Initialized n_window and n_poly QLineEdits with default values.")

        # Initialize specific settings selection
        self.spec_settings = QComboBox()
        self.spec_settings.addItems(["Nearest", "Other"])
        logger.debug("Initialized spec_settings ComboBox with items.")

        # Initialize apply button
        self.apply_button = QPushButton("apply")
        logger.debug("Initialized apply_button with label 'Apply'.")

        # Layout for smoothing method
        layout = QVBoxLayout()
        layout.addWidget(QLabel("smoothing method:"))
        layout.addWidget(self.smoothing_method)

        # Layout for window size
        layout_n_window = QVBoxLayout()
        layout_n_window.addWidget(QLabel("window size:"))
        layout_n_window.addWidget(self.n_window)

        # Layout for polynomial order
        layout_n_poly = QVBoxLayout()
        layout_n_poly.addWidget(QLabel("polynomial order:"))
        layout_n_poly.addWidget(self.n_poly)

        # Horizontal layout to place window size and polynomial order side by side
        h_layout = QHBoxLayout()
        h_layout.addLayout(layout_n_window)
        h_layout.addLayout(layout_n_poly)
        layout.addLayout(h_layout)

        # Layout for specific settings
        layout.addWidget(QLabel("specific settings:"))
        layout.addWidget(self.spec_settings)
        layout.addWidget(self.apply_button)

        self.layout().addLayout(layout)
        logger.debug("SmoothingBlock UI initialized successfully.")


class BackgroundSubtractionBlock(QWidget):
    """
    A QWidget subclass that provides UI components for selecting and configuring
    the background subtraction method applied to data.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayout(QVBoxLayout())

        # Initialize background subtraction method selection
        self.background_method = QComboBox()
        self.background_method.addItems(
            [
                "Linear",
                "Sigmoidal",
                "Tangential",
                "Left Tangential",
                "Left Sigmoidal",
                "Right Tangential",
                "Right Sigmoidal",
                "Bezier",
            ]
        )
        logger.debug("Initialized background_method ComboBox with items.")

        # Initialize range inputs
        self.range_left = QLineEdit()
        self.range_right = QLineEdit()
        logger.debug("Initialized range_left and range_right QLineEdits.")

        # Initialize apply button
        self.apply_button = QPushButton("apply")
        logger.debug("Initialized apply_button with label 'Apply'.")

        # Layout for background subtraction method
        layout = QVBoxLayout()
        layout.addWidget(QLabel("background subtraction method:"))
        layout.addWidget(self.background_method)

        # Layout for background subtraction range
        layout.addWidget(QLabel("background subtraction range:"))

        layout_range_left = QVBoxLayout()
        layout_range_left.addWidget(QLabel("left:"))
        layout_range_left.addWidget(self.range_left)

        layout_range_right = QVBoxLayout()
        layout_range_right.addWidget(QLabel("right:"))
        layout_range_right.addWidget(self.range_right)

        # Horizontal layout to place range inputs side by side
        h_layout = QHBoxLayout()
        h_layout.addLayout(layout_range_left)
        h_layout.addLayout(layout_range_right)
        layout.addLayout(h_layout)

        layout.addWidget(self.apply_button)
        self.layout().addLayout(layout)
        logger.debug("BackgroundSubtractionBlock UI initialized successfully.")


class ActionButtonsBlock(QWidget):
    """
    A QWidget subclass that provides action buttons for resetting changes
    and performing derivative operations.
    """

    # Define custom signals
    cancel_changes_clicked = pyqtSignal(dict)
    derivative_clicked = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayout(QVBoxLayout())

        # Initialize action buttons
        self.cancel_changes_button = QPushButton("reset changes")
        self.derivative_button = QPushButton("to da/dT")
        logger.debug("Initialized cancel_changes_button and derivative_button.")

        # Connect buttons to their respective slots with logging
        self.cancel_changes_button.clicked.connect(self.emit_cancel_changes_signal)
        self.derivative_button.clicked.connect(self.emit_derivative_signal)
        logger.debug("Connected buttons to their respective signal emitters.")

        # Add buttons to layout
        self.layout().addWidget(self.derivative_button)
        self.layout().addWidget(self.cancel_changes_button)
        logger.debug("ActionButtonsBlock UI initialized successfully.")

    def emit_cancel_changes_signal(self):
        """
        Emit the cancel_changes_clicked signal with the reset operation.
        """
        logger.debug("Cancel Changes button clicked. Emitting cancel_changes_clicked signal.")
        self.cancel_changes_clicked.emit({"operation": "reset"})

    def emit_derivative_signal(self):
        """
        Emit the derivative_clicked signal with the differential operation.
        """
        logger.debug("Derivative button clicked. Emitting derivative_clicked signal.")
        self.derivative_clicked.emit({"operation": "differential"})


class ExperimentSubBar(QWidget):
    """
    A QWidget subclass that serves as a sub-bar in the experiment application.
    It aggregates the smoothing, background subtraction, and action buttons blocks.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        logger.debug("ExperimentSubBar initialized successfully.")

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        logger.debug("Set up main vertical layout with top alignment.")

        # Initialize sub-components
        self.smoothing_block = SmoothingBlock(self)
        self.background_subtraction_block = BackgroundSubtractionBlock(self)
        self.action_buttons_block = ActionButtonsBlock(self)
        logger.debug("Initialized SmoothingBlock, BackgroundSubtractionBlock, and ActionButtonsBlock.")

        # Add sub-components to the main layout
        layout.addWidget(self.smoothing_block)
        layout.addWidget(self.background_subtraction_block)
        layout.addWidget(self.action_buttons_block)
        logger.debug("Added sub-components to the main layout.")

        self.updateGeometry()
        logger.debug("Updated geometry after initializing UI components.")

    def resizeEvent(self, event):
        """
        Handle the resize event to adjust the maximum width based on the parent widget.

        Args:
            event (QResizeEvent): The resize event.
        """
        super().resizeEvent(event)
        if self.parent():
            new_width = self.parent().width()
            self.setMaximumWidth(new_width)
            logger.debug(f"Resized ExperimentSubBar to match parent width: {new_width}px.")
        else:
            logger.warning("ExperimentSubBar has no parent to resize relative to.")
