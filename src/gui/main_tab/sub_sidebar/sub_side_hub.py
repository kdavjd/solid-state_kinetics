from gui.main_tab.sub_sidebar.model_based.model_based import ModelBasedTab
from gui.main_tab.sub_sidebar.model_free.deconvolution_sub_bar import DeconvolutionSubBar
from gui.main_tab.sub_sidebar.model_free.ea_sub_bar import EaSubBar
from gui.main_tab.sub_sidebar.model_free.experiment_sub_bar import ExperimentSubBar
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget


class SubSideHub(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)

        self.deconvolution_sub_bar = DeconvolutionSubBar(self)
        self.ea_sub_bar = EaSubBar(self)
        self.experiment_sub_bar = ExperimentSubBar(self)
        self.model_based = ModelBasedTab(self)

        self.deconvolution_sub_bar.hide()
        self.ea_sub_bar.hide()
        self.experiment_sub_bar.hide()
        self.model_based.hide()

        self.current_widget = None

    def update_content(self, content_type):
        if self.current_widget is not None:
            self.layout.removeWidget(self.current_widget)
            self.current_widget.hide()

        if content_type == "deconvolution":
            self.current_widget = self.deconvolution_sub_bar
        elif content_type == "Ea":
            self.current_widget = self.ea_sub_bar
        elif content_type == "experiments":
            self.current_widget = self.experiment_sub_bar
        elif content_type == "model_based":
            self.current_widget = self.model_based
        else:
            self.current_widget = QLabel("unknown content", self)

        self.current_widget.show()
        self.layout.addWidget(self.current_widget)
