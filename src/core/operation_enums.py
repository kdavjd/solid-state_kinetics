from enum import Enum


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
