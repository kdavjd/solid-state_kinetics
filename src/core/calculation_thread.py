from PyQt6.QtCore import QThread, pyqtSignal


class CalculationThread(QThread):
    result_ready = pyqtSignal(object)

    def __init__(self, calculation_func, *args, **kwargs):
        super().__init__()
        self.calculation_func = calculation_func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        result = self.calculation_func(*self.args, **self.kwargs)
        self.result_ready.emit(result)
