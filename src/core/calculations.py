from typing import Callable

import numpy as np
import pandas as pd
from core.basic_signals import BasicSignals
from core.calculation_thread import CalculationThread
from core.curve_fitting import CurveFitting as cft
from core.logger_config import logger
from core.logger_console import LoggerConsole as console
from PyQt6.QtCore import pyqtSignal, pyqtSlot
from scipy.optimize import OptimizeResult, differential_evolution


class Calculations(BasicSignals):
    new_best_result = pyqtSignal(dict)

    def __init__(self):
        super().__init__("calculations")
        self.thread: CalculationThread = None
        self.differential_evolution_results: list[tuple[np.ndarray, float]] = []
        self.best_combination = None
        self.best_mse = float("inf")
        self.new_best_result.connect(self.handle_new_best_result)

    def start_calculation_thread(self, func: Callable, *args, **kwargs) -> None:
        self.thread = CalculationThread(func, *args, **kwargs)
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
            reaction_variables = response["reaction_variables"]
            bounds = response["bounds"]
            reaction_combinations = response["reaction_combinations"]
            experimental_data = response["experimental_data"]
            deconvolution_settings: dict = response["deconvolution_settings"]
            deconvolution_method = deconvolution_settings.pop("method", "")
            deconvolution_parameters = deconvolution_settings.pop("deconvolution_parameters", {})

            target_function = self.generate_target_function(
                reaction_variables, reaction_combinations, experimental_data
            )
            if deconvolution_method == "differential_evolution":
                self.start_differential_evolution(
                    bounds=bounds, target_function=target_function, **deconvolution_parameters
                )
            else:
                logger.error(f"Неизвестный метод деконволюции: {deconvolution_method}")
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
                    self.new_best_result.emit(
                        {"best_mse": best_mse, "best_combination": best_combination, "params": params}
                    )
            return best_mse

        return target_function

    def start_differential_evolution(self, bounds, *args, **kwargs):
        if "target_function" not in kwargs:
            raise ValueError("Необходимо передать 'target_function' в аргументах kwargs")

        target_function = kwargs.pop("target_function")

        logger.debug(f"Начало дифференциальной эволюции с bounds: {bounds} и kwargs: {kwargs}")

        self.start_calculation_thread(
            differential_evolution,
            target_function,
            bounds=bounds,
            **kwargs,
        )

    def _save_intermediate_result(self, xk, convergence):
        self.differential_evolution_results.append((xk, convergence))
        logger.info(f"Промежуточный результат: xk = {xk}, convergence = {convergence}")

    @pyqtSlot(dict)
    def handle_new_best_result(self, result: dict):
        best_mse = result["best_mse"]
        best_combination = result["best_combination"]
        params = result["params"]
        if best_mse < self.best_mse:
            self.best_mse = best_mse
            self.best_combination = best_combination
            console.log(
                f"Новый лучший результат:\n"
                f"Лучшее MSE: {best_mse}\n"
                f"Комбинация реакций: {best_combination}\n\n"
                f"Параметры: {params}"
            )
            request_id = self.create_and_emit_request("main_tab", "get_file_name")
            file_name = self.handle_response_data(request_id)

            request_id = self.create_and_emit_request(
                "calculations_data_operations",
                "update_reactions_params",
                path_keys=[file_name],
                best_combination=best_combination,
                reactions_params=params,
            )
            _ = self.handle_response_data(request_id)

    @pyqtSlot(bool)
    def calc_data_operations_in_progress(self, in_progress: bool):
        pass
