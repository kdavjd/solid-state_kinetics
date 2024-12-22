from typing import Any, Dict, Optional

from core.base_signals import BaseSlots

from src.core.logger_config import logger


class SeriesData(BaseSlots):
    def __init__(self, actor_name: str = "series_data", signals=None):
        super().__init__(actor_name=actor_name, signals=signals)
        self.series: Dict[str, Any] = {}
        self.default_name_counter: int = 1

    def process_request(self, params: dict) -> None:
        """
        Handle incoming requests based on the 'operation' specified in params.

        Supported operations:
        - "add_series": Add a new series.
        - "delete_series": Delete an existing series.
        - "rename_series": Rename an existing series.
        - "get_all_series": Retrieve all series.
        - "get_series": Retrieve a specific series by name.

        Parameters
        ----------
        params : dict
            The request parameters, must include 'operation'.
        """
        operation = params.get("operation")
        logger.debug(f"{self.actor_name} processing operation: {operation}")

        response = {
            "actor": self.actor_name,
            "target": params.get("actor"),
            "request_id": params.get("request_id"),
            "data": None,
            "operation": operation,
        }

        if operation == "add_series":
            data = params.get("data")
            name = params.get("name")
            success, assigned_name = self.add_series(data=data, name=name)
            if success:
                response["data"] = True

        elif operation == "delete_series":
            name = params.get("name")
            success = self.delete_series(name=name)
            if success:
                response["data"] = True

        elif operation == "rename_series":
            old_name = params.get("old_name")
            new_name = params.get("new_name")
            success = self.rename_series(old_name=old_name, new_name=new_name)
            if success:
                response["data"] = True

        elif operation == "get_all_series":
            all_series = self.get_all_series()
            response["data"] = all_series

        elif operation == "get_series":
            name = params.get("name")
            series_data = self.get_series(name=name)
            if series_data is not None:
                response["data"] = True

        else:
            logger.error(f"Unknown operation '{operation}' received by {self.actor_name}")

        self.signals.response_signal.emit(response)

    def add_series(self, data: Any, name: Optional[str] = None):
        if name is None:
            name = f"Series {self.default_name_counter}"
            self.default_name_counter += 1
            logger.debug(f"Assigned default name: {name}")

        if name in self.series:
            logger.error(f"Series with name '{name}' already exists.")
            return False, None

        self.series[name] = data
        logger.info(f"Added series: {name}")
        return True, name

    def delete_series(self, name: str) -> bool:
        if name in self.series:
            del self.series[name]
            logger.info(f"Deleted series: {name}")
            return True
        else:
            logger.error(f"Series with name '{name}' not found.")
            return False

    def rename_series(self, old_name: str, new_name: str) -> bool:
        if old_name not in self.series:
            logger.error(f"Series with name '{old_name}' not found.")
            return False

        if new_name in self.series:
            logger.error(f"Series with name '{new_name}' already exists.")
            return False

        self.series[new_name] = self.series.pop(old_name)
        logger.info(f"Renamed series from '{old_name}' to '{new_name}'")
        return True

    def get_series(self, name: str) -> Optional[Any]:
        return self.series.get(name)

    def get_all_series(self) -> Dict[str, Any]:
        return self.series.copy()
