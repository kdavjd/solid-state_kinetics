import sys

from PyQt6.QtWidgets import QApplication

from core.file_data import FileData
from gui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    file_data = FileData()
    window.main_tab.sidebar.load_button.file_selected.connect(
        file_data.load_file)
    window.main_tab.sidebar.chosen_experiment_signal.connect(
        file_data.get_dataframe_copy)
    file_data.dataframe_signal.connect(
        window.main_tab.plot_canvas.plot_from_dataframe)
    file_data.data_loaded_signal.connect(
        window.main_tab.plot_canvas.plot_from_dataframe)
    file_data.data_loaded_signal.connect(
        window.table_tab.table_widget.display_dataframe)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
