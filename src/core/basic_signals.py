import uuid
from typing import Any

from core.logger_config import logger
from PyQt6.QtCore import QEventLoop, QObject, QTimer, pyqtSignal, pyqtSlot


class BasicSignals(QObject):
    request_signal = pyqtSignal(dict)
    response_signal = pyqtSignal(dict)

    def __init__(self, actor_name: str):
        super().__init__()
        self.actor_name = actor_name
        self.pending_requests: dict[str, Any] = {}
        self.event_loops: dict[str, Any] = {}

    def handle_request_cycle(self, target: str, operation: str, **kwargs) -> Any:
        """
        Создает запрос, отправляет его и ожидает ответа.

        :param target: Целевая система для запроса.
        :param operation: Операция, которая должна быть выполнена.
        :param kwargs: Дополнительные параметры для запроса.
        :return: Данные ответа, если запрос успешен, иначе None.
        """
        # Шаг 1: Создать и отправить запрос
        request_id = self.create_and_emit_request(target, operation, **kwargs)

        # Шаг 2: Ожидать данные ответа
        response_data = self.handle_response_data(request_id, operation)

        # Шаг 3: Вернуть данные ответа
        if response_data is not None:
            return response_data
        else:
            logger.error(f"{self.actor_name}_handle_request_cycle: {operation} completed with None")
            return None

    def create_and_emit_request(self, target: str, operation: str, **kwargs) -> str:
        request_id = str(uuid.uuid4())
        self.pending_requests[request_id] = {"received": False, "data": None}
        request = {
            "actor": self.actor_name,
            "target": target,
            "operation": operation,
            "request_id": request_id,
            **kwargs,
        }
        self.request_signal.emit(request)
        return request_id

    @pyqtSlot(dict)
    def response_slot(self, params: dict):
        if params["target"] != self.actor_name:
            return

        request_id = params.get("request_id")
        operaion = params.get("operation")
        logger.info(f"{self.actor_name}_response_slot: {operaion} completed")

        if request_id in self.pending_requests:
            self.pending_requests[request_id]["data"] = params
            self.pending_requests[request_id]["received"] = True

            if request_id in self.event_loops:
                self.event_loops[request_id].quit()
        else:
            logger.error(f"{self.actor_name}_response_slot: unknown UUID: {request_id}")

    def wait_for_response(self, request_id, timeout=1000):
        if request_id not in self.pending_requests:
            self.pending_requests[request_id] = {"received": False, "data": None}

        loop = QEventLoop()
        self.event_loops[request_id] = loop

        timed_out = False

        def on_timeout():
            nonlocal timed_out
            timed_out = True
            loop.quit()

        QTimer.singleShot(timeout, on_timeout)

        while not self.pending_requests[request_id]["received"] and not timed_out:
            loop.exec()

        del self.event_loops[request_id]

        if timed_out:
            logger.error(
                f"{self.actor_name}_wait_for_response: {request_id} waiting time has expired\n\
                waiting is stopped: {self.event_loops.get(request_id, None) is None}"
            )
            return None
        return self.pending_requests.pop(request_id)["data"]

    def handle_response_data(self, request_id: str, operation: str) -> Any:
        response_data = self.wait_for_response(request_id)
        if response_data is not None:
            return response_data.pop("data", None)
        else:
            logger.error(f"{self.actor_name}_handle_response: {operation} waiting time has expired")
            return None
