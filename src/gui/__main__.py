import sys

from core.calculations import Calculations
from core.calculations_data import CalculationsData
from core.calculations_data_operations import CalculationsDataOperations
from core.file_data import FileData
from core.file_operations import ActiveFileOperations
from gui.main_window import MainWindow
from PyQt6.QtWidgets import QApplication


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    file_data = FileData()
    calculations_data = CalculationsData()
    calcultaions = Calculations()
    calculations_data_operations = CalculationsDataOperations()
    file_operations = ActiveFileOperations()

    window.main_tab.sidebar.load_button.file_selected.connect(file_data.load_file)
    window.main_tab.sidebar.chosen_experiment_signal.connect(file_data.plot_dataframe_copy)
    window.main_tab.active_file_modify_signal.connect(file_operations.request_slot)
    window.main_tab.calculations_data_modify_signal.connect(calculations_data_operations.request_slot)
    window.main_tab.processing_signal.connect(calcultaions.calc_data_operations_in_progress)
    window.main_tab.request_signal.connect(calculations_data_operations.request_slot)
    file_data.plot_dataframe_signal.connect(window.main_tab.plot_canvas.plot_file_data_from_dataframe)
    file_data.data_loaded_signal.connect(window.main_tab.plot_canvas.plot_file_data_from_dataframe)
    file_data.data_loaded_signal.connect(window.table_tab.table_widget.display_dataframe)
    file_operations.request_signal.connect(file_data.request_slot)
    file_data.response_signal.connect(file_operations.response_slot)
    file_data.response_signal.connect(calculations_data_operations.response_slot)
    calculations_data_operations.plot_reaction.connect(window.main_tab.plot_canvas.plot_reaction)
    calculations_data_operations.reaction_params_to_gui.connect(
        window.main_tab.sub_sidebar.deconvolution_sub_bar.coeffs_table.fill_table
    )
    calculations_data_operations.reaction_params_to_gui.connect(window.main_tab.plot_canvas.add_anchors)
    calculations_data_operations.request_signal.connect(file_data.request_slot)
    calculations_data_operations.request_signal.connect(calculations_data.request_slot)
    calculations_data.response_signal.connect(calculations_data_operations.response_slot)
    calculations_data_operations.response_signal.connect(calcultaions.response_slot)
    calculations_data_operations.response_signal.connect(window.main_tab.response_slot)
    calculations_data_operations.deconvolution_signal.connect(calcultaions.run_deconvolution)

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
