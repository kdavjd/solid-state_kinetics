from functools import wraps
from itertools import product
from typing import Callable

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
        logger.debug(f"Calling {func.__name__} with args: {args} and kwargs: {kwargs}")
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
        self.best_combination = None
        self.best_mse = float('inf')

    def start_calculation_thread(self, func: Callable, *args, **kwargs) -> None:
        self.thread: Thread = Thread(func, *args, **kwargs)
        self.thread.result_ready.connect(self._calculation_finished)
        self.thread.start()

    @pyqtSlot(object)
    def _calculation_finished(self, result):
        try:
            console.log(f"Вычисления выполнены успешно.{result}")
        except ValueError as e:
            logger.error(f"Ошибка при обработке результата: {e}")

    @pyqtSlot(dict)
    def modify_active_file_slot(self, params: dict):
        self.active_file_operations.modify_active_file(params)

    @pyqtSlot(dict)
    def modify_calculations_data_slot(self, params: dict):
        response = self.calculations_data_operations.modify_calculations_data(params)
        if response:
            logger.info(f"response: {response}")
            self._prepare_and_start_optimization(response)

    def _prepare_and_start_optimization(self, response: dict):
        try:

            combined_keys = response['combined_keys']
            bounds = response['bounds']
            reaction_combinations = response['reaction_combinations']
            experimental_data = response['experimental_data']

            target_function = self.generate_target_function(combined_keys, reaction_combinations, experimental_data)

            self.start_differential_evolution(bounds=bounds, target_function=target_function)
        except Exception as e:
            logger.error(f"Ошибка при подготовке и запуске оптимизации: {e}")

    def generate_target_function(self, combined_keys: dict, reaction_combinations: list[tuple],
                                 experimental_data: pd.DataFrame):
        def target_function(params):
            best_mse = float('inf')
            # best_combination = None
            mse_dict = {}

            for combination in reaction_combinations:
                cumulative_function = np.zeros(len(experimental_data['temperature']))
                param_idx = 0
                for (reaction, coeffs), func in zip(combined_keys.items(), combination):
                    coeff_count = len(coeffs)
                    func_params = params[param_idx:param_idx + coeff_count]
                    param_idx += coeff_count

                    x = experimental_data['temperature']

                    if len(func_params) < 3:
                        raise ValueError("Not enough parameters for the function.")

                    h, z, w = func_params[0:3]  # First coefficients are universal for all functions
                    func_idx = 3
                    if func == 'gauss':
                        reaction_values = cft.gaussian(x, h, z, w)
                        cumulative_function += reaction_values

                    elif func == 'fraser':
                        fs = func_params[func_idx]
                        reaction_values = cft.fraser_suzuki(x, h, z, w, fs)
                        cumulative_function += reaction_values

                    elif func == 'ads':
                        ads1 = func_params[func_idx] if 'fs' not in coeffs else func_params[func_idx + 1]
                        ads2 = func_params[func_idx + 1] if 'fs' not in coeffs else func_params[func_idx + 2]
                        reaction_values = cft.asymmetric_double_sigmoid(x, h, z, w, ads1, ads2)
                        cumulative_function += reaction_values

                y_true = experimental_data.iloc[:, 1].to_numpy()
                mse = np.mean((y_true - cumulative_function) ** 2)
                mse_dict[combination] = mse

                if mse < best_mse:
                    best_mse = mse
                    # best_combination = combination

            return best_mse

        return target_function

    @add_default_kwargs
    def start_differential_evolution(self, bounds, *args, **kwargs):
        if 'target_function' not in kwargs:
            raise ValueError("Необходимо передать 'target_function' в аргументах kwargs")

        target_function = kwargs.pop('target_function')
        callback = kwargs.pop('callback', None)

        logger.debug(f"Starting differential evolution with bounds: {bounds} and kwargs: {kwargs}")

        self.start_calculation_thread(
            differential_evolution,
            target_function,
            bounds=bounds,
            callback=callback,
            **kwargs
        )

    def _save_intermediate_result(self, xk, convergence):
        self.differential_evolution_results.append((xk, convergence))
        logger.info(f"Промежуточный результат: xk = {xk}, convergence = {convergence}")


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
            response = operations[operation](path_keys, params)
        else:
            logger.warning("Неизвестная или отсутствующая операция над данными.")
        return response

    def extract_reaction_params(self, path_keys: list):
        reaction_params = self.calculations_data.get_value(path_keys)
        return cft.parse_reaction_params(reaction_params)

    def plot_reaction_curve(self, file_name, reaction_name, bound_label, params):
        x_min, x_max = params[0]
        x = np.linspace(x_min, x_max, 100)
        y = cft.calculate_reaction(params)
        curve_name = f"{reaction_name}_{bound_label}"
        self.calculations.plot_reaction.emit((file_name, curve_name), [x, y])

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
                    y = cft.calculate_reaction(reaction_params.get(bound_label, []))
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
        combined_keys = {}
        num_coefficients = {}
        bounds = []
        check_keys = ['h', 'z', 'w', 'fr', 'ads1', 'ads2']
        file_name = path_keys[0]
        chosen_functions = params.get('chosen_functions')
        if not chosen_functions:
            raise ValueError("chosen_functions is None or empty")

        functions_data = self.calculations_data.get_value([file_name])
        if not functions_data:
            raise ValueError(f"No functions data found for file: {file_name}")

        reaction_combinations = list(product(*chosen_functions.values()))

        for reaction_name in chosen_functions:
            combined_keys_set = set()
            reaction_params = functions_data[reaction_name]
            if not reaction_params:
                raise ValueError(f"No reaction params found for reaction: {reaction_name}")
            for reaction_type in chosen_functions[reaction_name]:
                allowed_keys = cft._get_allowed_keys_for_type(reaction_type)
                combined_keys_set.update(allowed_keys)
            combined_keys[reaction_name] = combined_keys_set
            lower_coeffs_tuple = reaction_params["lower_bound_coeffs"].values()
            upper_coeffs_tuple = reaction_params["upper_bound_coeffs"].values()
            filtered_pairs = [
                (lc, uc) for lc, uc, key in zip(lower_coeffs_tuple, upper_coeffs_tuple, check_keys)
                if key in combined_keys_set]
            bounds.extend(filtered_pairs)
            num_coefficients[reaction_name] = len(combined_keys_set)

        return {
            'combined_keys': combined_keys,
            'bounds': bounds,
            'reaction_combinations': reaction_combinations,
            'experimental_data': self.calculations.file_data.dataframe_copies[file_name],
        }
