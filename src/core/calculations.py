from functools import lru_cache, wraps

import numpy as np
import pandas as pd
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot
from scipy.optimize import differential_evolution

from core.calculation_thread import CalculationThread as Thread
from core.calculations_data import CalculationsData
from core.curve_fitting import CurveFitting as cft
from core.file_data import FileData
from core.logger_config import logger
from core.logger_console import LoggerConsole as console

DIFFERENTIAL_EVOLUTION_DEFAULT_KWARGS = {
    'strategy': 'best1bin',
    'maxiter': 1000,
    'popsize': 15,
    'tol': 0.01,
    'mutation': (0.5, 1),
    'recombination': 0.7,
    'seed': None,
    'callback': None,
    'disp': False,
    'polish': True,
    'init': 'latinhypercube',
    'atol': 0,
    'updating': 'deferred',
    'workers': 1,
    'constraints': ()
}


def add_default_kwargs(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        for key, value in DIFFERENTIAL_EVOLUTION_DEFAULT_KWARGS.items():
            kwargs.setdefault(key, value)
        return func(*args, **kwargs)
    return wrapper


class Calculations(QObject):
    plot_reaction = pyqtSignal(tuple, list)
    add_reaction_fail = pyqtSignal()
    reaction_params_to_gui = pyqtSignal(dict)

    def __init__(self, file_data: FileData, calculations_data: CalculationsData):
        super().__init__()
        self.file_data = file_data
        self.calculations_data = calculations_data
        self.thread = None
        self.calculations_data_operations = CalculationsDataOperations(self, file_data, calculations_data)
        self.active_file_operations = ActiveFileOperations(self, file_data)
        self.differential_evolution_results: list[tuple[np.ndarray, float]] = []

    def start_calculation_thread(self, func, *args, **kwargs):
        self.thread: Thread = Thread(func, *args, **kwargs)
        self.thread.result_ready.connect(self._calculation_finished)
        self.thread.start()

    @pyqtSlot(object)
    def _calculation_finished(self, result):
        try:
            pass
        except ValueError as e:
            logger.error(f"Ошибка при обработке результата: {e}")

    @pyqtSlot(dict)
    def modify_active_file_slot(self, params: dict):
        self.active_file_operations.modify_active_file(params)

    @pyqtSlot(dict)
    def modify_calculations_data_slot(self, params: dict):
        self.calculations_data_operations.modify_calculations_data(params)

    @add_default_kwargs
    def start_differential_evolution(self, bounds, *args, **kwargs):
        if 'target_function' not in kwargs:
            raise ValueError("Необходимо передать 'target_function' в аргументах kwargs")

        target_function = kwargs.pop('target_function')
        callback = self.save_intermediate_result

        self.start_calculation_thread(
            differential_evolution,
            target_function,
            bounds=bounds,
            callback=callback,
            *args, **kwargs
        )

    def save_intermediate_result(self, xk, convergence):
        self.differential_evolution_results.append((xk, convergence))
        logger.info(f"Промежуточный результат: xk = {xk}, convergence = {convergence}")

    def target_function(self):
        pass


class ActiveFileOperations:
    def __init__(self, calculations: Calculations, file_data: FileData):
        self.calculations = calculations
        self.file_data = file_data

    @pyqtSlot(dict)
    def modify_active_file(self, params: dict):
        logger.debug(f"В modify_active_file пришли данные {params}")
        operation = params.get("operation")
        file_name = params.get("file_name")
        if operation == "differential":
            self._apply_differential_operation(file_name, params)
        elif operation == "cancel_changes":
            self.file_data.reset_dataframe_copy(file_name)

    def diff_function(self, data: pd.DataFrame):
        return data.diff() * -1

    def _apply_differential_operation(self, file_name, params):
        if not self.file_data.check_operation_executed(file_name, "differential"):
            self.file_data.modify_data(self.diff_function, params)
        else:
            console.log("Данные уже приведены к da/dT")


class CalculationsDataOperations:
    def __init__(self, calculations: Calculations, file_data: FileData, calculations_data: CalculationsData):
        self.calculations = calculations
        self.file_data = file_data
        self.calculations_data = calculations_data

    @pyqtSlot(dict)
    def modify_calculations_data(self, params: dict):
        logger.debug(f"В modify_calculations_data пришли данные {params}")
        path_keys = params.get("path_keys")
        operation = params.get("operation")

        if not path_keys or not isinstance(path_keys, list):
            logger.error("Некорректный или пустой список path_keys")
            return

        operations = {
            "add_reaction": self.add_reaction,
            "remove_reaction": self.remove_reaction,
            "highlight_reaction": self.highlight_reaction,
            "update_value": self.update_value,
            "deconvolution": self.deconvolution
        }

        if operation in operations:
            operations[operation](path_keys, params)
        else:
            logger.warning("Неизвестная или отсутствующая операция над данными.")

    def extract_reaction_params(self, path_keys: list):
        reaction_params = self.calculations_data.get_value(path_keys)
        return cft.parse_reaction_params(reaction_params)

    def plot_reaction_curve(self, file_name, reaction_name, bound_label, params):
        x_min, x_max = params[0]
        x = np.linspace(x_min, x_max, 100)
        y = self.calculate_reaction(params)
        curve_name = f"{reaction_name}_{bound_label}"
        self.calculations.plot_reaction.emit((file_name, curve_name), [x, y])

    @lru_cache(maxsize=128)
    def calculate_reaction(self, reaction_params: tuple):
        x_range, function_type, coeffs = reaction_params
        x = np.linspace(x_range[0], x_range[1], 100)
        result = None
        if function_type == "gauss":
            result = cft.gaussian(x, *coeffs)
        elif function_type == "fraser":
            result = cft.fraser_suzuki(x, *coeffs)
        elif function_type == "ads":
            result = cft.asymmetric_double_sigmoid(x, *coeffs)
        return result

    def add_reaction(self, path_keys: list, _params: dict):
        file_name, reaction_name = path_keys
        if not self.file_data.check_operation_executed(file_name, "differential"):
            console.log("Данные нужно привести к da/dT")
            self.calculations.add_reaction_fail.emit()
            return

        df = self.file_data.dataframe_copies[file_name]
        data = cft.generate_default_function_data(df)
        self.calculations_data.set_value(path_keys.copy(), data)
        reaction_params = self.extract_reaction_params(path_keys)

        for bound_label, params in reaction_params.items():
            self.plot_reaction_curve(file_name, reaction_name, bound_label, params)

    def remove_reaction(self, path_keys: list, _params: dict):
        if len(path_keys) < 2:
            logger.error("Недостаточно информации в path_keys для удаления реакции")
            return
        file_name, reaction_name = path_keys
        if self.calculations_data.exists(path_keys):
            self.calculations_data.remove_value(path_keys)
            logger.debug(f"Удалена реакция {reaction_name} для файла {file_name}")
            console.log(f"Реакция {reaction_name} была успешно удалена")
        else:
            logger.warning(f"Реакция {reaction_name} не найдена в данных")
            console.log(f"Не удалось найти реакцию {reaction_name} для удаления")

    def highlight_reaction(self, path_keys: list, _params: dict):
        file_name = path_keys[0]
        self.file_data.plot_dataframe_signal.emit(self.file_data.dataframe_copies[file_name])
        data = self.calculations_data.get_value([file_name])
        reactions = data.keys()

        cumulative_y = {
            "upper_bound_coeffs": np.array([]),
            "lower_bound_coeffs": np.array([]),
            "coeffs": np.array([]),
        }
        x = None

        for reaction_name in reactions:
            reaction_params = self.extract_reaction_params([file_name, reaction_name])
            for bound_label, params in reaction_params.items():
                if bound_label in cumulative_y:
                    y = self.calculate_reaction(reaction_params.get(bound_label, []))
                    if x is None:
                        x_min, x_max = params[0]
                        x = np.linspace(x_min, x_max, 100)
                    cumulative_y[bound_label] = cumulative_y[bound_label] + y if cumulative_y[bound_label].size else y

            if reaction_name in path_keys:
                self.calculations.reaction_params_to_gui.emit(reaction_params)
                self.plot_reaction_curve(
                    file_name, reaction_name, "upper_bound_coeffs", reaction_params.get("upper_bound_coeffs", []))
                self.plot_reaction_curve(
                    file_name, reaction_name, "lower_bound_coeffs", reaction_params.get("lower_bound_coeffs", []))
            else:
                self.plot_reaction_curve(file_name, reaction_name, "coeffs", reaction_params.get("coeffs", []))

        for bound_label, y in cumulative_y.items():
            self.calculations.plot_reaction.emit((file_name, f'cumulative_{bound_label}'), [x, y])

    def _update_coeffs_value(self, path_keys: list[str], new_value):
        bound_keys = ['upper_bound_coeffs', 'lower_bound_coeffs']
        for key in bound_keys:
            if key in path_keys:
                opposite_key = bound_keys[1 - bound_keys.index(key)]
                new_keys = path_keys.copy()
                new_keys[new_keys.index(key)] = opposite_key
                opposite_value = self.calculations_data.get_value(new_keys)

                average_value = (new_value + opposite_value) / 2
                new_keys[new_keys.index(opposite_key)] = 'coeffs'
                self.calculations_data.set_value(new_keys, average_value)
                logger.info(f"Данные по пути: {new_keys}\n изменены на: {average_value}")

    def update_value(self, path_keys: list[str], params: dict):
        try:
            new_value = params.get('value')
            if self.calculations_data.exists(path_keys):
                self.calculations_data.set_value(path_keys.copy(), new_value)
                logger.info(f"Данные по пути: {path_keys}\n изменены на: {new_value}")

                self._update_coeffs_value(path_keys.copy(), new_value)
                self.highlight_reaction(path_keys[:2], params)
            else:
                logger.error(f"Все данные: {self.calculations_data._data}")
                logger.error(f"Данных по пути: {path_keys} не найдено.")
        except ValueError as e:
            logger.error(f"Непредусмотренная ошибка при обновлении данных по пути: {path_keys}: {str(e)}")

    def deconvolution(self, path_keys: list[str], params: dict):
        reaction_settings = params.get('reaction_settings')
        file_name = path_keys[0]
        model_of_experimental_data = self.calculations_data.get_value([file_name])
        # experimental_data = self.calculations.file_data.dataframe_copies[file_name]

        reaction_bounds = cft._generate_reaction_bounds(reaction_settings, model_of_experimental_data)
        logger.debug(f"reaction_bounds: {reaction_bounds}")
