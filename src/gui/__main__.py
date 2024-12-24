import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

from core.base_signals import BaseSignals
from PyQt6.QtWidgets import QApplication

from src.core.calculations import Calculations
from src.core.calculations_data import CalculationsData
from src.core.calculations_data_operations import CalculationsDataOperations
from src.core.file_data import FileData
from src.core.file_operations import ActiveFileOperations
from src.core.series_data import SeriesData
from src.gui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    signals = BaseSignals()
    window = MainWindow(signals=signals)
    file_data = FileData(signals=signals)
    series_data = SeriesData(signals=signals)  # noqa: F841
    calculations_data = CalculationsData(signals=signals)  # noqa: F841
    calculations = Calculations(signals=signals)
    calculations_data_operations = CalculationsDataOperations(signals=signals)
    file_operations = ActiveFileOperations(signals=signals)  # noqa: F841

    window.main_tab.sidebar.load_button.file_selected.connect(file_data.load_file)
    window.main_tab.sidebar.chosen_experiment_signal.connect(file_data.plot_dataframe_copy)
    file_data.data_loaded_signal.connect(window.main_tab.plot_canvas.plot_data_from_dataframe)
    calculations_data_operations.reaction_params_to_gui.connect(window.main_tab.plot_canvas.add_anchors)
    file_data.data_loaded_signal.connect(window.table_tab.table_widget.display_dataframe)
    calculations_data_operations.plot_reaction.connect(window.main_tab.plot_canvas.plot_reaction)
    calculations_data_operations.deconvolution_signal.connect(calculations.run_deconvolution)
    calculations_data_operations.reaction_params_to_gui.connect(
        window.main_tab.sub_sidebar.deconvolution_sub_bar.coeffs_table.fill_table
    )

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
