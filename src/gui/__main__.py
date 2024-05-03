import sys

from PyQt6.QtWidgets import QApplication

from core.calculations import Calcultaions
from core.calculations_data import CalculationsData
from core.file_data import FileData
from gui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    file_data = FileData()
    calculations_data = CalculationsData()
    calcultaions = Calcultaions(file_data, calculations_data)
    window.main_tab.sidebar.load_button.file_selected.connect(
        file_data.load_file)
    window.main_tab.sidebar.chosen_experiment_signal.connect(
        file_data.plot_dataframe_copy)
    file_data.plot_dataframe_signal.connect(
        window.main_tab.plot_canvas.plot_from_dataframe)
    file_data.data_loaded_signal.connect(
        window.main_tab.plot_canvas.plot_from_dataframe)
    file_data.data_loaded_signal.connect(
        window.table_tab.table_widget.display_dataframe)
    window.main_tab.active_file_modify_signal.connect(calcultaions.modify_active_file_slot)
    window.main_tab.calculations_data_modify_signal.connect(calcultaions.modify_calculations_data_slot)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
