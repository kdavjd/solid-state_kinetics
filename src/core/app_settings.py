from enum import Enum

import numpy as np


class OperationType(Enum):
    ADD_REACTION = "add_reaction"
    REMOVE_REACTION = "remove_reaction"
    HIGHLIGHT_REACTION = "highlight_reaction"
    DIFFERENTIAL = "differential"
    RESET_FILE_DATA = "reset_file_data"
    IMPORT_REACTIONS = "import_reactions"
    EXPORT_REACTIONS = "export_reactions"
    DECONVOLUTION = "deconvolution"
    STOP_CALCULATION = "stop_calculation"
    MODEL_BASED_CALCULATION = "model_based_calculation"
    GET_FILE_NAME = "get_file_name"
    PLOT_DF = "plot_df"
    PLOT_MSE_LINE = "plot_mse_line"
    CALCULATION_FINISHED = "calculation_finished"
    UPDATE_VALUE = "update_value"
    ADD_NEW_SERIES = "add_new_series"
    DELETE_SERIES = "delete_series"
    GET_ALL_SERIES = "get_all_series"
    GET_SERIES = "get_series"
    RENAME_SERIES = "rename_series"
    UPDATE_REACTIONS_PARAMS = "update_reactions_params"
    GET_VALUE = "get_value"
    SET_VALUE = "set_value"
    REMOVE_VALUE = "remove_value"
    GET_FULL_DATA = "get_full_data"
    CHECK_DIFFERENTIAL = "check_differential"
    GET_DF_DATA = "get_df_data"
    GET_ALL_DATA = "get_all_data"
    LOAD_FILE = "load_file"
    SCHEME_CHANGE = "scheme_change"
    MODEL_PARAMS_CHANGE = "model_params_change"
    SELECT_SERIES = "select_series"


MODEL_BASED_DIFFERENTIAL_EVOLUTION_DEFAULT_KWARGS = {
    "strategy": "best1bin",
    "maxiter": 60,
    "popsize": 3,
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

MODEL_FREE_DIFFERENTIAL_EVOLUTION_DEFAULT_KWARGS = {
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


NUC_MODELS_TABLE = {
    "F1/3": {"differential_form": lambda e: (3 / 2) * e ** (1 / 3), "integral_form": lambda e: 1 - e ** (2 / 3)},
    "F3/4": {"differential_form": lambda e: 4 * e ** (3 / 4), "integral_form": lambda e: 1 - e ** (1 / 4)},
    "F3/2": {"differential_form": lambda e: 2 * e ** (3 / 2), "integral_form": lambda e: e ** (-1 / 2) - 1},
    "F2": {"differential_form": lambda e: e**2, "integral_form": lambda e: e ** (-1) - 1},
    "F3": {"differential_form": lambda e: e**3, "integral_form": lambda e: e ** (-2) - 1},
    "F1/A1": {"differential_form": lambda e: e, "integral_form": lambda e: -np.log(e)},
    "A2": {
        "differential_form": lambda e: 2 * e * (-np.log(e)) ** (1 / 2),
        "integral_form": lambda e: (-np.log(e)) ** (1 / 2),
    },
    "A3": {
        "differential_form": lambda e: 3 * e * (-np.log(e)) ** (2 / 3),
        "integral_form": lambda e: (-np.log(e)) ** (1 / 3),
    },
    "A4": {
        "differential_form": lambda e: 4 * e * (-np.log(e)) ** (3 / 4),
        "integral_form": lambda e: (-np.log(e)) ** (1 / 4),
    },
    "A2/3": {
        "differential_form": lambda e: (2 / 3) * e * (-np.log(e)) ** (-1 / 2),
        "integral_form": lambda e: (-np.log(e)) ** (3 / 2),
    },
    "A3/2": {
        "differential_form": lambda e: (3 / 2) * e * (-np.log(e)) ** (1 / 3),
        "integral_form": lambda e: (-np.log(e)) ** (2 / 3),
    },
    "A3/4": {
        "differential_form": lambda e: (3 / 4) * e * (-np.log(e)) ** (-1 / 3),
        "integral_form": lambda e: (-np.log(e)) ** (4 / 3),
    },
    "A5/2": {
        "differential_form": lambda e: (5 / 2) * e * (-np.log(e)) ** (3 / 5),
        "integral_form": lambda e: (-np.log(e)) ** (2 / 5),
    },
    "F0/R1/P1": {"differential_form": lambda e: np.full_like(e, 1), "integral_form": lambda e: 1 - e},
    "R2": {"differential_form": lambda e: 2 * e ** (1 / 2), "integral_form": lambda e: 1 - e ** (1 / 2)},
    "R3": {"differential_form": lambda e: 3 * e ** (2 / 3), "integral_form": lambda e: 1 - e ** (1 / 3)},
    "P3/2": {
        "differential_form": lambda e: (2 / 3) / (1 - e) ** (1 / 2),
        "integral_form": lambda e: (1 - e) ** (3 / 2),
    },
    "P2": {"differential_form": lambda e: 2 * (1 - e) ** (1 / 2), "integral_form": lambda e: (1 - e) ** (1 / 2)},
    "P3": {"differential_form": lambda e: 3 * (1 - e) ** (2 / 3), "integral_form": lambda e: (1 - e) ** (1 / 3)},
    "P4": {"differential_form": lambda e: 4 * (1 - e) ** (3 / 4), "integral_form": lambda e: (1 - e) ** (1 / 4)},
    "E1": {"differential_form": lambda e: 1 - e, "integral_form": lambda e: np.log(1 - e)},
    "E2": {"differential_form": lambda e: (1 - e) / 2, "integral_form": lambda e: np.log((1 - e) ** 2)},
    "D1": {"differential_form": lambda e: 1 / (2 * (1 - e)), "integral_form": lambda e: (1 - e) ** 2},
    "D2": {"differential_form": lambda e: 1 / (-np.log(e)), "integral_form": lambda e: (1 - e) + e * np.log(e)},
    "D3": {
        "differential_form": lambda e: ((3 / 2) * e ** (2 / 3)) / (1 - e ** (1 / 3)),
        "integral_form": lambda e: (1 - e ** (1 / 3)) ** 2,
    },
    "D4": {
        "differential_form": lambda e: (3 / 2) / (e ** (-1 / 3) - 1),
        "integral_form": lambda e: 1 - (2 * (1 - e) / 3) - e ** (2 / 3),
    },
    "D5": {
        "differential_form": lambda e: ((3 / 2) * e ** (4 / 3)) / (e ** (-1 / 3) - 1),
        "integral_form": lambda e: (e ** (-1 / 3) - 1) ** 2,
    },
    "D6": {
        "differential_form": lambda e: ((3 / 2) * (1 + e) ** (2 / 3)) / ((1 + e) ** (1 / 3) - 1),
        "integral_form": lambda e: ((1 + e) ** (1 / 3) - 1) ** 2,
    },
    "D7": {
        "differential_form": lambda e: (3 / 2) / (1 - (1 + e) ** (-1 / 3)),
        "integral_form": lambda e: 1 + (2 * (1 - e) / 3) - (1 + e) ** (2 / 3),
    },
    "D8": {
        "differential_form": lambda e: ((3 / 2) * (1 + e) ** (4 / 3)) / (1 - (1 + e) ** (-1 / 3)),
        "integral_form": lambda e: ((1 + e) ** (-1 / 3) - 1) ** 2,
    },
    "G1": {"differential_form": lambda e: 1 / (2 * e), "integral_form": lambda e: 1 - e**2},
    "G2": {"differential_form": lambda e: 1 / (3 * e**2), "integral_form": lambda e: 1 - e**3},
    "G3": {"differential_form": lambda e: 1 / (4 * e**3), "integral_form": lambda e: 1 - e**4},
    "G4": {"differential_form": lambda e: (1 / 2) * e * (-np.log(e)), "integral_form": lambda e: (-np.log(e)) ** 2},
    "G5": {
        "differential_form": lambda e: (1 / 3) * e * (-np.log(e)) ** 2,
        "integral_form": lambda e: (-np.log(e)) ** 3,
    },
    "G6": {
        "differential_form": lambda e: (1 / 4) * e * (-np.log(e)) ** 3,
        "integral_form": lambda e: (-np.log(e)) ** 4,
    },
    "G7": {
        "differential_form": lambda e: (1 / 4) * e ** (1 / 2) / (1 - e ** (1 / 2)),
        "integral_form": lambda e: (1 - e ** (1 / 2)) ** (1 / 2),
    },
    "G8": {
        "differential_form": lambda e: (1 / 3) * e ** (2 / 3) / (1 - e ** (1 / 3)),
        "integral_form": lambda e: (1 - e ** (1 / 3)) ** (1 / 2),
    },
    "B1": {"differential_form": lambda e: 1 / ((1 - e) - e), "integral_form": lambda e: np.log((1 - e) / e)},
}


def clamp_fraction(e, eps=1e-8):
    if e < eps:
        e = eps
    elif e > 1 - eps:
        e = 1 - eps
    return e


def clamp_fraction_decorator(eps=1e-8):
    def decorator(func):
        def wrapper(e, *args, **kwargs):
            e_clamped = clamp_fraction(e, eps=eps)
            return func(e_clamped, *args, **kwargs)

        return wrapper

    return decorator


NUC_MODELS_LIST = sorted(NUC_MODELS_TABLE.keys())
for key in NUC_MODELS_LIST:
    if key in NUC_MODELS_TABLE:
        df = NUC_MODELS_TABLE[key]["differential_form"]
        NUC_MODELS_TABLE[key]["differential_form"] = clamp_fraction_decorator()(df)
