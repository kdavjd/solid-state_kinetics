import time
from itertools import product

import numpy as np
from core.basic_signals import BasicSignals
from core.curve_fitting import CurveFitting as cft
from core.logger_config import logger
from core.logger_console import LoggerConsole as console
from PyQt6.QtCore import pyqtSignal, pyqtSlot


class CalculationsDataOperations(BasicSignals):
    deconvolution_signal = pyqtSignal(dict)
    plot_reaction = pyqtSignal(tuple, list)
    reaction_params_to_gui = pyqtSignal(dict)

    def __init__(self):
        super().__init__("calculations_data_operations")
        self.last_plot_time = 0
        self.calculations_in_progress = False

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

    def _protected_plot_update_curves(self, path_keys, params):
        if self.calculations_in_progress:
            return
        current_time = time.time()
        if current_time - self.last_plot_time >= 0.5:
            self.last_plot_time = current_time
            self.highlight_reaction(path_keys, params)

    def _extract_reaction_params(self, path_keys: list):
        request_id = self.create_and_emit_request("calculations_data", "get_value", path_keys=path_keys)
        reaction_params = self.handle_response(request_id)
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
        is_executed = self.handle_response(request_id)

        if is_executed:
            request_id = self.create_and_emit_request("file_data", "get_df_data", file_name=file_name)
            df = self.handle_response(request_id)

            data = cft.generate_default_function_data(df)
            request_id = self.create_and_emit_request(
                "calculations_data", "set_value", path_keys=path_keys.copy(), value=data
            )
            is_exist = self.handle_response(request_id)
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
        is_exist = self.handle_response(request_id)
        if not is_exist:
            logger.warning(f"Реакция {reaction_name} не найдена в данных")
            console.log(f"Не удалось найти реакцию {reaction_name} для удаления")
        logger.debug(f"Удалена реакция {reaction_name} для файла {file_name}")
        console.log(f"Реакция {reaction_name} была успешно удалена")

    def highlight_reaction(self, path_keys: list, _params: dict):
        file_name = path_keys[0]
        request_id = self.create_and_emit_request("file_data", "plot_dataframe", file_name=file_name)
        if not self.handle_response(request_id):
            logger.warning("Ответ от file_data не получен")

        request_id = self.create_and_emit_request("calculations_data", "get_value", path_keys=[file_name])
        data = self.handle_response(request_id)

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
                opposite_value = self.handle_response(request_id)

                average_value = (new_value + opposite_value) / 2
                new_keys[new_keys.index(opposite_key)] = "coeffs"
                request_id = self.create_and_emit_request(
                    "calculations_data", "set_value", path_keys=new_keys, value=average_value
                )
                is_exist = self.handle_response(request_id)
                if is_exist:
                    logger.info(f"Данные по пути: {new_keys} изменены на: {average_value}")
                else:
                    logger.error(f"Данных по пути: {new_keys} не найдено.")

    def update_value(self, path_keys: list[str], params: dict):
        try:
            new_value = params.get("value")
            is_chain = params.get("is_chain", None)
            request_id = self.create_and_emit_request(
                "calculations_data", "set_value", path_keys=path_keys.copy(), value=new_value
            )
            is_ok = self.handle_response(request_id)
            if is_ok:
                logger.info(f"Данные по пути: {path_keys} изменены на: {new_value}")
                if not is_chain:
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
        functions_data = self.handle_response(request_id)

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

        request_id = self.create_and_emit_request("file_data", "get_df_data", file_name=file_name)
        df = self.handle_response(request_id)

        return {
            "combined_keys": combined_keys,
            "bounds": bounds,
            "reaction_combinations": reaction_combinations,
            "experimental_data": df,
        }
