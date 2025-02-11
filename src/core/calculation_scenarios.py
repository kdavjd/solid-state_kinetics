from multiprocessing import Manager
from typing import Callable, Dict

import numpy as np
from scipy.integrate import solve_ivp

from src.core.app_settings import NUC_MODELS_TABLE
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


class ModelBasedScenario(BaseCalculationScenario):
    def get_result_strategy_type(self) -> str:
        return "model_based_calculation"

    def get_optimization_method(self) -> str:
        return self.params.get("calculation_settings", {}).get("method", "differential_evolution")

    def get_bounds(self) -> list[tuple]:
        """
        Для каждой реакции задаём три параметра:
          1. logA: [log_A_min, log_A_max]
          2. Ea:   [Ea_min, Ea_max]
          3. contribution: [contribution_min, contribution_max]
        """
        scheme = self.params.get("reaction_scheme")
        if not scheme:
            raise ValueError("No 'reaction_scheme' provided for ModelBasedScenario.")
        reactions = scheme.get("reactions")
        if not reactions:
            raise ValueError("No 'reactions' in reaction_scheme.")

        bounds = []
        # Ограничения для logA
        for reaction in reactions:
            logA_min = reaction.get("log_A_min", 0)
            logA_max = reaction.get("log_A_max", 10)
            bounds.append((logA_min, logA_max))
        # Ограничения для Ea
        for reaction in reactions:
            Ea_min = reaction.get("Ea_min", 1)  # Если не передано, значения по умолчанию в джоулях
            Ea_max = reaction.get("Ea_max", 2000)
            bounds.append((Ea_min, Ea_max))

        for reaction in reactions:
            contrib_min = reaction.get("contribution_min", 0)
            contrib_max = reaction.get("contribution_max", 1)
            bounds.append((contrib_min, contrib_max))
        return bounds

    def get_target_function(self) -> Callable:
        scheme = self.params.get("reaction_scheme")
        reactions = scheme.get("reactions")
        components = scheme.get("components")

        species_list = [comp["id"] for comp in components]
        num_species = len(species_list)
        num_reactions = len(reactions)

        experimental_data = self.params.get("experimental_data")
        if experimental_data is None:
            raise ValueError("No 'experimental_data' provided for ModelBasedScenario.")

        exp_temperature = experimental_data["temperature"].to_numpy() + 273.15

        betas = [float(col) for col in experimental_data.columns if col.lower() != "temperature"]

        all_exp_masses = []
        for beta in betas:
            col_name = str(beta)
            if col_name not in experimental_data.columns:
                col_name = str(int(beta))
            if col_name not in experimental_data.columns:
                raise ValueError(f"Experimental data does not contain column for beta value {beta}")
            exp_mass = experimental_data[col_name].to_numpy()
            all_exp_masses.append(exp_mass)

        manager = Manager()
        best_mse = manager.Value("d", np.inf)
        lock = manager.Lock()

        return ModelBasedTargetFunction(
            species_list, reactions, num_species, num_reactions, betas, all_exp_masses, exp_temperature, best_mse, lock
        )


class ModelBasedTargetFunction:
    def __init__(
        self,
        species_list,
        reactions,
        num_species,
        num_reactions,
        betas,
        all_exp_masses,
        exp_temperature,
        best_mse,
        lock,
    ):
        self.species_list = species_list
        self.reactions = reactions
        self.num_species = num_species
        self.num_reactions = num_reactions
        self.betas = betas
        self.all_exp_masses = all_exp_masses
        self.exp_temperature = exp_temperature
        self.best_mse = best_mse
        self.lock = lock
        self.R = 8.314

    def __call__(self, X: np.ndarray) -> float:
        # sum_contrib = np.sum(X[2 * self.num_reactions : 3 * self.num_reactions])
        # if not np.isclose(sum_contrib, 1.0, atol=1e-4):
        #     return 1e12

        total_mse = 0.0

        def ode_func(T, X, beta):
            dXdt = np.zeros_like(X)
            conc = X[: self.num_species]
            beta_SI = beta / 60.0
            for i in range(self.num_reactions):
                src = self.reactions[i]["from"]
                tgt = self.reactions[i]["to"]
                src_index = self.species_list.index(src)
                tgt_index = self.species_list.index(tgt)
                e_value = conc[src_index]
                reaction_type = self.reactions[i]["reaction_type"]
                model = NUC_MODELS_TABLE.get(reaction_type)
                if model is None:
                    logger.warning(f"Unknown reaction type '{reaction_type}'. Using linear dependence.")
                    f_e = e_value
                else:
                    f_e = model["differential_form"](e_value)

                k_i = (10 ** (X[i]) * np.exp(-X[self.num_reactions + i] * 1000 / (self.R * T))) / beta_SI
                rate = k_i * f_e
                dXdt[src_index] -= rate
                dXdt[tgt_index] += rate
                dXdt[self.num_species + i] = rate
            return dXdt

        for i, beta_val in enumerate(self.betas):
            exp_mass_i = self.all_exp_masses[i]
            T_array = self.exp_temperature
            X0 = np.zeros(self.num_species + self.num_reactions)
            if self.num_species > 0:
                X0[0] = 1.0
            try:
                sol = solve_ivp(
                    lambda T, vec: ode_func(T, vec, beta_val),
                    [T_array[0], T_array[-1]],
                    X0,
                    t_eval=T_array,
                    method="RK45",
                )
                if not sol.success:
                    return 1e12

                ints = sol.y[self.num_species : self.num_species + self.num_reactions, :]
                M0 = exp_mass_i[0]
                Mfin = exp_mass_i[-1]
                contributions = X[2 * self.num_reactions : 3 * self.num_reactions]
                int_sum = np.sum(contributions[:, np.newaxis] * ints, axis=0)
                model_mass = M0 - (M0 - Mfin) * int_sum
                mse_i = np.mean((model_mass - exp_mass_i) ** 2)
                total_mse += mse_i
            except Exception as e:
                logger.error(f"Error in ODE integration: {e}")
                return 1e12

        with self.lock:
            if total_mse < self.best_mse.value:
                self.best_mse.value = total_mse

        return total_mse


SCENARIO_REGISTRY = {
    "deconvolution": DeconvolutionScenario,
    "model_based_calculation": ModelBasedScenario,
}
