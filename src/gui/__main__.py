import sys

from PyQt6.QtWidgets import QApplication

from src.core.basic_signals import SignalDispatcher
from src.core.calculations import Calculations
from src.core.calculations_data import CalculationsData
from src.core.calculations_data_operations import CalculationsDataOperations
from src.core.file_data import FileData
from src.core.file_operations import ActiveFileOperations
from src.gui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    dispatcher = SignalDispatcher()
    window = MainWindow(dispatcher=dispatcher)
    file_data = FileData(dispatcher=dispatcher)
    calculations_data = CalculationsData(dispatcher=dispatcher)  # noqa: F841
    calculations = Calculations(dispatcher=dispatcher)
    calculations_data_operations = CalculationsDataOperations(dispatcher=dispatcher)
    file_operations = ActiveFileOperations(dispatcher=dispatcher)  # noqa: F841

    window.main_tab.sidebar.load_button.file_selected.connect(file_data.load_file)
    window.main_tab.sidebar.chosen_experiment_signal.connect(file_data.plot_dataframe_copy)
    window.main_tab.processing_signal.connect(calculations.calc_data_operations_in_progress)
    file_data.data_loaded_signal.connect(window.main_tab.plot_canvas.plot_file_data_from_dataframe)
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
