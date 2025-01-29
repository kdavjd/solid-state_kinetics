from typing import Any, Optional

from src.core.base_signals import BaseSlots
from src.core.logger_config import logger
from src.core.operation_enums import OperationType


class SeriesData(BaseSlots):
    def __init__(self, actor_name: str = "series_data", signals=None):
        super().__init__(actor_name=actor_name, signals=signals)
        self.series = {}
        self.default_name_counter: int = 1

    def process_request(self, params: dict) -> None:
        operation = params.get("operation")
        logger.debug(f"{self.actor_name} processing operation: {operation}")

        response = {
            "actor": self.actor_name,
            "target": params.get("actor"),
            "request_id": params.get("request_id"),
            "data": None,
            "operation": operation,
        }

        def handle_add_new_series(p: dict, r: dict) -> None:
            data = p.get("data")
            name = p.get("name")
            success, assigned_name = self.add_series(data=data, name=name)
            r["data"] = success

        def handle_delete_series(p: dict, r: dict) -> None:
            name = p.get("name")
            success = self.delete_series(series_name=name)
            r["data"] = success

        def handle_rename_series(p: dict, r: dict) -> None:
            old_name = p.get("old_name")
            new_name = p.get("new_name")
            success = self.rename_series(old_series_name=old_name, new_series_name=new_name)
            r["data"] = success

        def handle_get_all_series(p: dict, r: dict) -> None:
            r["data"] = self.get_all_series()

        def handle_get_series(p: dict, r: dict) -> None:
            series_name = p.get("series_name")
            info_type = p.get("info_type", "experimental")
            series_data = self.get_series(series_name=series_name, info_type=info_type)
            r["data"] = series_data

        def handle_scheme_change(p: dict, r: dict):
            series_name = p.get("series_name")
            new_scheme = p.get("reaction_scheme", {})
            success = self.update_series(series_name, new_scheme)
            r["data"] = success

        operations_map = {
            OperationType.ADD_NEW_SERIES: handle_add_new_series,
            OperationType.DELETE_SERIES: handle_delete_series,
            OperationType.RENAME_SERIES: handle_rename_series,
            OperationType.GET_ALL_SERIES: handle_get_all_series,
            OperationType.GET_SERIES: handle_get_series,
            OperationType.SCHEME_CHANGE: handle_scheme_change,
        }

        handler = operations_map.get(operation)
        if handler is not None:
            handler(params, response)
        else:
            logger.error(f"Unknown operation '{operation}' received by {self.actor_name}")

        self.signals.response_signal.emit(response)

    def _get_default_reaction_params(self, series_name: str):
        default_params = {
            "reaction_type": "F1",
            "Ea": 120,
            "log_A": 8,
            "contribution": 0.5,
            "Ea_min": 1,
            "Ea_max": 2000,
            "log_A_min": 0.1,
            "log_A_max": 100,
            "contribution_min": 0.01,
            "contribution_max": 1,
        }

        series_entry = self.series.get(series_name)
        if not series_entry:
            logger.warning(f"Series '{series_name}' not found for adding default reaction params.")
            return

        reaction_scheme = series_entry.get("reaction_scheme", {})
        reactions = reaction_scheme.get("reactions", [])

        for reaction in reactions:
            for key, value in default_params.items():
                if key not in reaction:
                    reaction[key] = value

        self.series[series_name]["reaction_scheme"] = reaction_scheme

    def add_series(self, data: Any, name: Optional[str] = None):
        if name is None:
            name = f"Series {self.default_name_counter}"
            self.default_name_counter += 1
            logger.debug(f"Assigned default name: {name}")

        if name in self.series:
            logger.error(f"Series with name '{name}' already exists.")
            return False, None

        reaction_scheme = {
            "components": [{"id": "A"}, {"id": "B"}],
            "reactions": [
                {
                    "from": "A",
                    "to": "B",
                }
            ],
        }

        self.series[name] = {"experimental_data": data, "reaction_scheme": reaction_scheme}

        self._get_default_reaction_params(name)

        return True, name

    def update_series(self, series_name: str, new_scheme: dict) -> bool:
        series_entry = self.series.get(series_name)
        if not series_entry:
            logger.error(f"Series '{series_name}' not found; cannot update scheme.")
            return False

        old_scheme = series_entry.get("reaction_scheme", {})
        # old_components = old_scheme.get("components", [])
        old_reactions = old_scheme.get("reactions", [])

        new_components = new_scheme.get("components", [])
        old_scheme["components"] = new_components

        new_reactions_data = new_scheme.get("reactions", [])

        old_reactions_map = {(r["from"], r["to"]): r for r in old_reactions}

        updated_reactions = []
        for nr in new_reactions_data:
            key = (nr.get("from"), nr.get("to"))
            if key in old_reactions_map:
                old_reaction = old_reactions_map[key]
                merged_reaction = {**old_reaction, **nr}
                updated_reactions.append(merged_reaction)
            else:
                updated_reactions.append(nr)

        old_scheme["reactions"] = updated_reactions
        series_entry["reaction_scheme"] = old_scheme

        self._get_default_reaction_params(series_name)

        logger.info(f"Updated scheme for series '{series_name}'.")
        return True

    def delete_series(self, series_name: str) -> bool:
        if series_name in self.series:
            del self.series[series_name]
            logger.info(f"Deleted series: {series_name}")
            return True
        else:
            logger.error(f"Series with name '{series_name}' not found.")
            return False

    def rename_series(self, old_series_name: str, new_series_name: str) -> bool:
        if old_series_name not in self.series:
            logger.error(f"Series with name '{old_series_name}' not found.")
            return False

        if new_series_name in self.series:
            logger.error(f"Series with name '{new_series_name}' already exists.")
            return False

        self.series[new_series_name] = self.series.pop(old_series_name)
        logger.info(f"Renamed series from '{old_series_name}' to '{new_series_name}'")
        return True

    def get_series(self, series_name: str, info_type: str = "experimental"):
        series_entry: dict = self.series.get(series_name)
        if not series_entry:
            return None

        if info_type == "experimental":
            return series_entry.get("experimental_data", None)
        elif info_type == "scheme":
            return series_entry.get("reaction_scheme", None)
        elif info_type == "all":
            return series_entry
        else:
            logger.warning(f"Unknown info_type='{info_type}'. Returning all data by default.")
            return series_entry

    def get_all_series(self):
        return self.series.copy()
