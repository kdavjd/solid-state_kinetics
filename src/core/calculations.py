import time
import uuid
from functools import wraps
from itertools import product
from typing import Any, Callable

import numpy as np
import pandas as pd
from core.calculation_thread import CalculationThread as Thread
from core.curve_fitting import CurveFitting as cft
from core.logger_config import logger
from core.logger_console import LoggerConsole as console
from PyQt6.QtCore import QEventLoop, QObject, QTimer, pyqtSignal, pyqtSlot
from scipy.optimize import OptimizeResult, differential_evolution

DIFFERENTIAL_EVOLUTION_DEFAULT_KWARGS = {
    "strategy": "best1bin",
    "maxiter": 1000,
    "popsize": 15,
    "tol": 0.01,
    "mutation": (0.5, 1),
    "recombination": 0.7,
    "seed": None,
    "callback": None,
    "disp": False,
    "polish": True,
    "init": "latinhypercube",
    "atol": 0,
    "updating": "deferred",
    "workers": 1,
    "constraints": (),
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
    request_signal = pyqtSignal(dict)
    new_best_result = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.thread = None
        self.differential_evolution_results: list[tuple[np.ndarray, float]] = []
        self.best_combination = None
        self.pending_requests: dict[str, Any] = {}
        self.event_loops: dict[str, Any] = {}
        self.best_mse = float("inf")
        self.new_best_result.connect(self.handle_new_best_result)

    def create_and_emit_request(self, target: str, operation: str, **kwargs) -> str:
        request_id = str(uuid.uuid4())
        self.pending_requests[request_id] = {"received": False, "data": None}
        request = {
            "actor": "calculations",
            "target": target,
            "operation": operation,
            "request_id": request_id,
            **kwargs,
        }
        logger.debug(f"create_and_emit_request: request data: {request}")
        self.request_signal.emit(request)
        return request_id

    @pyqtSlot(dict)
    def response_slot(self, params: dict):
        if params["target"] != "calculations":
            return

        request_id = params.get("request_id")

        if request_id in self.pending_requests:
            logger.debug(f"calculations_request_slot: Обработка запроса с UUID: {request_id}")
            self.pending_requests[request_id]["data"] = params
            self.pending_requests[request_id]["received"] = True

            if request_id in self.event_loops:
                logger.debug(f"calculations_request_slot: Завершаем цикл ожидания для UUID: {request_id}")
                self.event_loops[request_id].quit()
        else:
            logger.error(f"calculations_request_slot: Ответ с неизвестным UUID: {request_id}")

    def wait_for_response(self, request_id, timeout=1000):
        if request_id not in self.pending_requests:
            logger.debug(f"wait_for_response: Регистрация запроса UUID: {request_id} в pending_requests")
            self.pending_requests[request_id] = {"received": False, "data": None}

        loop = QEventLoop()
        self.event_loops[request_id] = loop
        QTimer.singleShot(timeout, loop.quit)

        while not self.pending_requests[request_id]["received"]:
            logger.debug(f"wait_for_response: Ожидание... UUID: {request_id}")
            loop.exec()

        del self.event_loops[request_id]
        return self.pending_requests.pop(request_id)["data"]

    def start_calculation_thread(self, func: Callable, *args, **kwargs) -> None:
        self.thread: Thread = Thread(func, *args, **kwargs)
        self.thread.result_ready.connect(self._calculation_finished)
        self.thread.start()

    @pyqtSlot(object)
    def _calculation_finished(self, result):
        try:
            if isinstance(result, OptimizeResult):
                x = result.x
                fun = result.fun
                success = result.success
                message = result.message

                console.log(
                    f"Вычисления выполнены успешно.\n"
                    f"Оптимальные параметры: {x}\n"
                    f"Значение целевой функции: {fun}\n"
                    f"Статус успеха: {success}\n"
                    f"Сообщение: {message}"
                )

                self.best_combination = x
                self.best_mse = fun
            else:
                console.log(f"Вычисления выполнены успешно. Результат: {result}")

        except ValueError as e:
            logger.error(f"Ошибка при обработке результата: {e}")

    @pyqtSlot(dict)
    def run_deconvolution(self, response: dict):
        logger.debug(f"run_deconvolution: response: {response}")
        try:
            combined_keys = response["combined_keys"]
            bounds = response["bounds"]
            reaction_combinations = response["reaction_combinations"]
            experimental_data = response["experimental_data"]

            target_function = self.generate_target_function(combined_keys, reaction_combinations, experimental_data)

            self.start_differential_evolution(bounds=bounds, target_function=target_function)
        except Exception as e:
            logger.error(f"Ошибка при подготовке и запуске оптимизации: {e}")

    def generate_target_function(
        self,
        combined_keys: dict,
        reaction_combinations: list[tuple],
        experimental_data: pd.DataFrame,
    ):
        def target_function(params):
            best_mse = float("inf")
            best_combination = None
            mse_dict = {}
            for combination in reaction_combinations:
                cumulative_function = np.zeros(len(experimental_data["temperature"]))
                param_idx = 0
                for (reaction, coeffs), func in zip(combined_keys.items(), combination):
                    coeff_count = len(coeffs)
                    func_params = params[param_idx : param_idx + coeff_count]
                    param_idx += coeff_count

                    x = experimental_data["temperature"]

                    if len(func_params) < 3:
                        raise ValueError("Not enough parameters for the function.")

                    h, z, w = func_params[0:3]  # First coefficients are universal for all functions
                    func_idx = 3
                    if func == "gauss":
                        reaction_values = cft.gaussian(x, h, z, w)
                        cumulative_function += reaction_values

                    if func == "fraser":
                        fs = func_params[func_idx]
                        reaction_values = cft.fraser_suzuki(x, h, z, w, fs)
                        cumulative_function += reaction_values

                    if func == "ads":
                        ads1 = func_params[func_idx] if "fs" not in coeffs else func_params[func_idx + 1]
                        ads2 = func_params[func_idx + 1] if "fs" not in coeffs else func_params[func_idx + 2]
                        reaction_values = cft.asymmetric_double_sigmoid(x, h, z, w, ads1, ads2)
                        cumulative_function += reaction_values

                y_true = experimental_data.iloc[:, 1].to_numpy()
                mse = np.mean((y_true - cumulative_function) ** 2)
                mse_dict[combination] = mse
                if mse < best_mse:
                    best_mse = mse
                    best_combination = combination
            self.new_best_result.emit({"best_mse": best_mse, "best_combination": best_combination})
            return best_mse

        return target_function

    @add_default_kwargs
    def start_differential_evolution(self, bounds, *args, **kwargs):
        if "target_function" not in kwargs:
            raise ValueError("Необходимо передать 'target_function' в аргументах kwargs")

        target_function = kwargs.pop("target_function")
        callback = kwargs.pop("callback", None)

        logger.debug(f"Starting differential evolution with bounds: {bounds} and kwargs: {kwargs}")

        self.start_calculation_thread(
            differential_evolution,
            target_function,
            bounds=bounds,
            callback=callback,
            **kwargs,
        )

    def _save_intermediate_result(self, xk, convergence):
        self.differential_evolution_results.append((xk, convergence))
        logger.info(f"Промежуточный результат: xk = {xk}, convergence = {convergence}")

    @pyqtSlot(dict)
    def handle_new_best_result(self, result: dict):
        best_mse = result["best_mse"]
        best_combination = result["best_combination"]
        if best_mse < self.best_mse:
            self.best_mse = best_mse
            self.best_combination = best_combination
            console.log(
                f"Новый лучший результат:\n" f"Лучшее MSE: {best_mse}\n" f"Комбинация реакций: {best_combination}\n\n"
            )

    @pyqtSlot(bool)
    def calc_data_operations_in_progress(self, in_progress: bool):
        pass


class CalculationsDataOperations(QObject):
    request_signal = pyqtSignal(dict)
    response_signal = pyqtSignal(dict)
    deconvolution_signal = pyqtSignal(dict)
    plot_reaction = pyqtSignal(tuple, list)
    reaction_params_to_gui = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.last_plot_time = 0
        self.calculations_in_progress = False
        self.pending_requests: dict[str, Any] = {}
        self.event_loops: dict[str, Any] = {}

    @pyqtSlot(dict)
    def request_slot(self, params: dict):
        if params["target"] != "calculations_data_operations":
            return
        logger.debug(f"В request_slot пришли данные {params}")
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
            "deconvolution": self.deconvolution,
        }

        if operation in operations:
            params["data"] = True
            answer = operations[operation](path_keys, params)
            if answer:
                if operation == "update_value":
                    self._protected_plot_update_curves(path_keys, params)

                if operation == "deconvolution":
                    self.deconvolution_signal.emit(answer)

            params["target"], params["actor"] = params["actor"], params["target"]
            self.response_signal.emit(params)
        else:
            logger.warning("Неизвестная или отсутствующая операция над данными.")

    @pyqtSlot(dict)
    def response_slot(self, params: dict):
        if params["target"] != "calculations_data_operations":
            return

        request_id = params.get("request_id")

        if request_id in self.pending_requests:
            logger.debug(f"response_slot: Обработка запроса с UUID: {request_id}")
            self.pending_requests[request_id]["data"] = params
            self.pending_requests[request_id]["received"] = True

            if request_id in self.event_loops:
                logger.debug(f"response_slot: Завершаем цикл ожидания для UUID: {request_id}")
                self.event_loops[request_id].quit()
        else:
            logger.error(f"response_slot: Ответ с неизвестным UUID: {request_id}")

    def create_and_emit_request(self, target: str, operation: str, **kwargs) -> str:
        request_id = str(uuid.uuid4())
        self.pending_requests[request_id] = {"received": False, "data": None}
        request = {
            "actor": "calculations_data_operations",
            "target": target,
            "operation": operation,
            "request_id": request_id,
            **kwargs,
        }
        self.request_signal.emit(request)
        return request_id

    def wait_for_response(self, request_id, timeout=1000):
        if request_id not in self.pending_requests:
            logger.debug(f"wait_for_response: Регистрация запроса UUID: {request_id} в pending_requests")
            self.pending_requests[request_id] = {"received": False, "data": None}

        loop = QEventLoop()
        self.event_loops[request_id] = loop
        QTimer.singleShot(timeout, loop.quit)

        while not self.pending_requests[request_id]["received"]:
            logger.debug(f"wait_for_response: Ожидание... UUID: {request_id}")
            loop.exec()

        del self.event_loops[request_id]
        return self.pending_requests.pop(request_id)["data"]

    def _protected_plot_update_curves(self, path_keys, params):
        if self.calculations_in_progress:
            return
        current_time = time.time()
        if current_time - self.last_plot_time >= 0.5:
            self.last_plot_time = current_time
            self.highlight_reaction(path_keys, params)

    def _extract_reaction_params(self, path_keys: list):
        request_id = self.create_and_emit_request("calculations_data", "get_value", path_keys=path_keys)
        reaction_params = self.wait_for_response(request_id).pop("data", None)
        return cft.parse_reaction_params(reaction_params)

    def _plot_reaction_curve(self, file_name, reaction_name, bound_label, params):
        x_min, x_max = params[0]
        x = np.linspace(x_min, x_max, 100)
        y = cft.calculate_reaction(params)
        curve_name = f"{reaction_name}_{bound_label}"
        self.plot_reaction.emit((file_name, curve_name), [x, y])

    def add_reaction(self, path_keys: list, _params: dict):
        file_name, reaction_name = path_keys

        request_id = self.create_and_emit_request("file_data", "check_differential", file_name=file_name)
        response_data = self.wait_for_response(request_id)
        is_executed = response_data.pop("data", None)

        if is_executed:
            df_data_request_id = self.create_and_emit_request("file_data", "get_df_data", file_name=file_name)
            df = self.wait_for_response(df_data_request_id).pop("data", None)

            data = cft.generate_default_function_data(df)
            request_id = self.create_and_emit_request(
                "calculations_data", "set_value", path_keys=path_keys.copy(), value=data
            )
            is_exist = self.wait_for_response(request_id).pop("data", None)
            if is_exist:
                logger.warning(f"Данные по пути: {path_keys.copy()} уже существуют")

            reaction_params = self._extract_reaction_params(path_keys)
            for bound_label, params in reaction_params.items():
                self._plot_reaction_curve(file_name, reaction_name, bound_label, params)
        else:
            _params["data"] = False

    def remove_reaction(self, path_keys: list, _params: dict):
        if len(path_keys) < 2:
            logger.error("Недостаточно информации в path_keys для удаления реакции")
            return
        file_name, reaction_name = path_keys
        request_id = self.create_and_emit_request("calculations_data", "remove_value", path_keys=path_keys)
        is_exist = self.wait_for_response(request_id).pop("data", None)
        if not is_exist:
            logger.warning(f"Реакция {reaction_name} не найдена в данных")
            console.log(f"Не удалось найти реакцию {reaction_name} для удаления")
        logger.debug(f"Удалена реакция {reaction_name} для файла {file_name}")
        console.log(f"Реакция {reaction_name} была успешно удалена")

    def highlight_reaction(self, path_keys: list, _params: dict):
        file_name = path_keys[0]
        request_id = self.create_and_emit_request("file_data", "plot_dataframe", file_name=file_name)
        if not self.wait_for_response(request_id).pop("data", None):
            logger.warning("Ответ от file_data не получен")

        request_id = self.create_and_emit_request("calculations_data", "get_value", path_keys=[file_name])
        data = self.wait_for_response(request_id).pop("data", None)

        reactions = data.keys()

        cumulative_y = {
            "upper_bound_coeffs": np.array([]),
            "lower_bound_coeffs": np.array([]),
            "coeffs": np.array([]),
        }
        x = None

        for reaction_name in reactions:
            reaction_params = self._extract_reaction_params([file_name, reaction_name])
            for bound_label, params in reaction_params.items():
                if bound_label in cumulative_y:
                    y = cft.calculate_reaction(reaction_params.get(bound_label, []))
                    if x is None:
                        x_min, x_max = params[0]
                        x = np.linspace(x_min, x_max, 100)
                    cumulative_y[bound_label] = cumulative_y[bound_label] + y if cumulative_y[bound_label].size else y

            if reaction_name in path_keys:
                self.reaction_params_to_gui.emit(reaction_params)
                self._plot_reaction_curve(
                    file_name,
                    reaction_name,
                    "upper_bound_coeffs",
                    reaction_params.get("upper_bound_coeffs", []),
                )
                self._plot_reaction_curve(
                    file_name,
                    reaction_name,
                    "lower_bound_coeffs",
                    reaction_params.get("lower_bound_coeffs", []),
                )
            else:
                self._plot_reaction_curve(
                    file_name,
                    reaction_name,
                    "coeffs",
                    reaction_params.get("coeffs", []),
                )

        for bound_label, y in cumulative_y.items():
            self.plot_reaction.emit((file_name, f"cumulative_{bound_label}"), [x, y])

    def _update_coeffs_value(self, path_keys: list[str], new_value):
        bound_keys = ["upper_bound_coeffs", "lower_bound_coeffs"]
        for key in bound_keys:
            if key in path_keys:
                opposite_key = bound_keys[1 - bound_keys.index(key)]
                new_keys = path_keys.copy()
                new_keys[new_keys.index(key)] = opposite_key

                request_id = self.create_and_emit_request("calculations_data", "get_value", path_keys=new_keys)
                opposite_value = self.wait_for_response(request_id).pop("data", None)

                average_value = (new_value + opposite_value) / 2
                new_keys[new_keys.index(opposite_key)] = "coeffs"
                request_id = self.create_and_emit_request(
                    "calculations_data", "set_value", path_keys=new_keys, value=average_value
                )
                is_exist = self.wait_for_response(request_id).pop("data", None)
                if is_exist:
                    logger.info(f"Данные по пути: {new_keys} изменены на: {average_value}")
                else:
                    logger.error(f"Данных по пути: {new_keys} не найдено.")

    def update_value(self, path_keys: list[str], params: dict):
        try:
            new_value = params.get("value")
            request_id = self.create_and_emit_request(
                "calculations_data", "set_value", path_keys=path_keys.copy(), value=new_value
            )
            is_exist = self.wait_for_response(request_id).pop("data", None)
            if is_exist:
                logger.info(f"Данные по пути: {path_keys} изменены на: {new_value}")
                self._update_coeffs_value(path_keys.copy(), new_value)
                return {"operation": "update_value", "data": None}
            else:
                logger.error(f"Данных по пути: {path_keys} не найдено.")
        except ValueError as e:
            logger.error(f"Непредусмотренная ошибка при обновлении данных по пути: {path_keys}: {str(e)}")

    def deconvolution(self, path_keys: list[str], params: dict):
        combined_keys = {}
        num_coefficients = {}
        bounds = []
        check_keys = ["h", "z", "w", "fr", "ads1", "ads2"]
        file_name = path_keys[0]
        chosen_functions = params.get("chosen_functions")
        if not chosen_functions:
            raise ValueError("chosen_functions is None or empty")

        request_id = self.create_and_emit_request("calculations_data", "get_value", path_keys=[file_name])
        functions_data = self.wait_for_response(request_id).pop("data", None)

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
                (lc, uc)
                for lc, uc, key in zip(lower_coeffs_tuple, upper_coeffs_tuple, check_keys)
                if key in combined_keys_set
            ]
            bounds.extend(filtered_pairs)
            num_coefficients[reaction_name] = len(combined_keys_set)

        df_data_request_id = self.create_and_emit_request("file_data", "get_df_data", file_name=file_name)
        df = self.wait_for_response(df_data_request_id).pop("data", None)

        return {
            "combined_keys": combined_keys,
            "bounds": bounds,
            "reaction_combinations": reaction_combinations,
            "experimental_data": df,
        }
