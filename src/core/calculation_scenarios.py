from typing import Callable, Dict

import numpy as np

from src.core.curve_fitting import CurveFitting as cft
from src.core.logger_config import logger


class BaseCalculationScenario:
    def __init__(self, params: Dict, calculations):
        self.params = params
        self.calculations = calculations

    def get_bounds(self) -> list[tuple]:
        raise NotImplementedError

    def get_target_function(self) -> Callable:
        raise NotImplementedError

    def get_optimization_method(self) -> str:
        return "differential_evolution"

    def get_result_strategy_type(self) -> str:
        raise NotImplementedError


class DeconvolutionScenario(BaseCalculationScenario):
    def get_bounds(self) -> list[tuple]:
        return self.params["bounds"]

    def get_optimization_method(self) -> str:
        deconv_settings = self.params.get("deconvolution_settings", {})
        return deconv_settings.pop("method", "differential_evolution")

    def get_result_strategy_type(self) -> str:
        return "deconvolution"

    def get_target_function(self) -> Callable:
        reaction_variables = self.params["reaction_variables"]
        reaction_combinations = self.params["reaction_combinations"]
        experimental_data = self.params["experimental_data"]

        def target_function(params_array: np.ndarray) -> float:
            if not self.calculations.calculation_active:
                return float("inf")

            best_mse = float("inf")
            best_combination = None

            for combination in reaction_combinations:
                cumulative_function = np.zeros(len(experimental_data["temperature"]))

                param_idx_local = 0

                for (reaction, coeffs), func in zip(reaction_variables.items(), combination):
                    coeff_count = len(coeffs)
                    func_params = params_array[param_idx_local : param_idx_local + coeff_count]
                    param_idx_local += coeff_count

                    x = experimental_data["temperature"]

                    # Для всех функций первые 3 params: h, z, w
                    if len(func_params) < 3:
                        raise ValueError("Not enough parameters for the function.")
                    h, z, w = func_params[0:3]

                    if func == "gauss":
                        reaction_values = cft.gaussian(x, h, z, w)
                    elif func == "fraser":
                        fr = func_params[3]  # fraser_suzuki
                        reaction_values = cft.fraser_suzuki(x, h, z, w, fr)
                    elif func == "ads":
                        ads1 = func_params[3]
                        ads2 = func_params[4]
                        reaction_values = cft.asymmetric_double_sigmoid(x, h, z, w, ads1, ads2)
                    else:
                        logger.warning(f"Unknown function type: {func}")
                        reaction_values = 0

                    cumulative_function += reaction_values

                y_true = experimental_data.iloc[:, 1].to_numpy()
                mse = np.mean((y_true - cumulative_function) ** 2)
                if mse < best_mse:
                    best_mse = mse
                    best_combination = combination

                    self.calculations.new_best_result.emit(
                        {"best_mse": best_mse, "best_combination": best_combination, "params": params_array}
                    )

            return best_mse

        return target_function


# class ModelBasedScenario(BaseCalculationScenario):
#     """
#     Сценарий "модельного расчёта".
#     Переносим сюда:
#       - generate_ode_system
#       - create_model_based_target_function
#     """

#     def get_result_strategy_type(self) -> str:
#         return "model_based_calculation"

#     def get_optimization_method(self) -> str:
#         return self.params.get("model_based_settings", {}).get("method", "differential_evolution")

#     def get_bounds(self) -> list[tuple]:
#         """
#         Раньше это было в run_model_based_calculation:
#           - считаем num_reactions = len(ode_system)
#           - формируем bounds (A, Ea, n)
#         """
#         scheme = self.params.get("scheme")
#         if not scheme:
#             raise ValueError("No 'scheme' provided for ModelBasedScenario.")

#         # Генерируем систему ОДУ, чтобы узнать, сколько реакций
#         ode_system = self._generate_ode_system(scheme)
#         num_reactions = len(ode_system)

#         # Примерно как было в вашем коде
#         bounds = (
#             [(0.01, 15.0) for _ in range(num_reactions)]
#             + [(40000.0, 200000.0) for _ in range(num_reactions)]
#             + [(0.01, 4.0) for _ in range(num_reactions)]
#         )
#         return bounds

#     def get_target_function(self) -> Callable:
#         scheme = self.params.get("scheme")
#         series_df = self.params.get("series_df")

#         if not scheme or series_df is None:
#             raise ValueError("Missing 'scheme' or 'series_df' in params")

#         # Генерируем систему ОДУ
#         ode_system = self._generate_ode_system(scheme)

#         def target_function(parameters: np.ndarray) -> float:
#             try:
#                 # Логика как в вашем create_model_based_target_function
#                 temperature = series_df["temperature"].to_numpy()
#                 experimental_data = series_df.drop(columns=["temperature"]).to_numpy()

#                 num_reactions = len(ode_system)
#                 A = 10 ** parameters[:num_reactions]  # К примеру, если так
#                 Ea = parameters[num_reactions : 2 * num_reactions]
#                 n = parameters[2 * num_reactions : 3 * num_reactions]

#                 R = 8.3144598

#                 # Считаем константы скорости
#                 rate_constants = A[:, np.newaxis] * np.exp(-Ea[:, np.newaxis] / (R * temperature))

#                 # Допустим, у нас num_species = len(ode_system.keys())
#                 species = list(ode_system.keys())
#                 num_species = len(species)

#                 # Задаём начальные концентрации (пример)
#                 X0 = np.zeros(num_species)
#                 X0[0] = 1.0

#                 # Для упрощения сделаем: reaction_matrix[r, from_idx, from_idx] -= 1
#                 # Вычислим его по ode_system
#                 reaction_matrix = np.zeros((num_reactions, num_species, num_species))

#                 # ode_system — dict {species_name: expression_str}
#                 # Но чтобы упростить, сделаем вид, что у нас есть список reaction_pairs
#                 # (from_s, to_s)
#                 reaction_pairs = self._extract_reactions_from_ode_system(ode_system)
#                 species_index = {s: i for i, s in enumerate(species)}

#                 for r, (from_s, to_s) in enumerate(reaction_pairs):
#                     from_idx = species_index[from_s]
#                     to_idx = species_index[to_s]
#                     reaction_matrix[r, from_idx, from_idx] -= 1
#                     reaction_matrix[r, to_idx, to_idx] += 1

#                 # Функция для solve_ivp
#                 def ode_func(t, X):
#                     idx = np.argmin(np.abs(temperature - t))
#                     k = rate_constants[:, idx]
#                     # пример некой модели, зависящей от X
#                     dXdt = np.sum(reaction_matrix * k[:, np.newaxis, np.newaxis] * X, axis=0).sum(axis=1)
#                     return dXdt

#                 sol = solve_ivp(ode_func, [temperature[0], temperature[-1]], X0, t_eval=temperature, method="RK45")

#                 if not sol.success:
#                     logger.warning(f"ODE solver failed: {sol.message}")
#                     return np.inf

#                 # sol.y shape = (num_species, len(temperature))
#                 # а experimental_data той же размерности?
#                 mse = np.mean((sol.y.T - experimental_data) ** 2)
#                 return mse

#             except Exception as e:
#                 logger.error(f"Error in model-based target function: {e}")
#                 return np.inf

#         return target_function

#     def _generate_ode_system(self, scheme: dict) -> dict:
#         """
#         Раньше было в calculations.generate_ode_system
#         Теперь — сугубо для данного сценария,
#         поэтому мы переносим её внутрь ModelBasedScenario как вспомогательный метод.
#         """
#         nodes = [node["id"] for node in scheme["nodes"]]

#         outgoing = {node: [] for node in nodes}
#         incoming = {node: [] for node in nodes}

#         for edge in scheme["edges"]:
#             source = edge["from"]
#             target = edge["to"]
#             outgoing[source].append(target)
#             incoming[target].append(source)

#         equations = {}
#         for node in nodes:
#             consumption_terms = [f"k_{node}_{to} * [{node}]" for to in outgoing[node]]
#             formation_terms = [f"k_{source}_to_{node} * [{source}]" for source in incoming[node]]

#             formation = " + ".join(formation_terms) if formation_terms else "0"
#             consumption = " + ".join(consumption_terms) if consumption_terms else "0"
#             equation = f"{formation} - ({consumption})"
#             equations[node] = equation

#         logger.debug(f"Generated ODE system: {equations}")
#         return equations

#     def _extract_reactions_from_ode_system(self, ode_system: dict) -> list[tuple[str, str]]:
#         """
#         Примерный метод, вычленяющий (from_s, to_s) из уравнений:
#         Например, если в equation: "k_A_B * [A]" => реакция (A, B).
#         Это упрощённый парсер, зависит от формата ваших уравнений.
#         """
#         reaction_pairs = []
#         for species_name, expr in ode_system.items():
#             # expr может быть вида: "k_A_B * [A] + k_C_D * [C] - (k_E_F * [E])"
#             # Разбиваем и ищем substr "k_X_Y"
#             # Супер-простой парсер:
#             tokens = expr.replace("(", "").replace(")", "").replace("-", "+").split("+")
#             for token in tokens:
#                 token = token.strip()
#                 if "k_" in token:
#                     # вычленяем "k_A_B"
#                     k_part = token.split("*")[0].strip()
#                     # k_part = "k_A_B" или "k_C_D" ...
#                     # делим по '_'
#                     _, from_s, to_s = k_part.split("_")
#                     reaction_pairs.append((from_s, to_s))
#         return list(set(reaction_pairs))


SCENARIO_REGISTRY = {
    "deconvolution": DeconvolutionScenario,
    # "model_based_calculation": ModelBasedScenario,
}
