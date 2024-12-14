import uuid
from typing import Any, Callable, Dict, Optional

from PyQt6.QtCore import QEventLoop, QObject, QTimer, pyqtSignal, pyqtSlot

from src.core.logger_config import logger


class SignalDispatcher(QObject):
    """A dispatcher that routes requests and responses between components.

    This class defines a simple mechanism for connecting components (actors)
    through signals. Each component can register itself with the dispatcher,
    specifying methods for handling requests and responses. Requests and
    responses are emitted as Qt signals.
    """

    request_signal = pyqtSignal(dict)
    response_signal = pyqtSignal(dict)

    def __init__(self):
        """Initialize the SignalDispatcher."""
        super().__init__()
        self.components: Dict[str, (Callable[[dict], None], Callable[[dict], None])] = {}
        self.request_signal.connect(self.dispatch_request)
        self.response_signal.connect(self.dispatch_response)

    def register_component(
        self,
        component_name: str,
        process_request_method: Callable[[dict], None],
        process_response_method: Callable[[dict], None],
    ) -> None:
        """Register a component with the dispatcher.

        Args:
            component_name (str): The name of the component.
            process_request_method (Callable[[dict], None]): A method for handling requests.
            process_response_method (Callable[[dict], None]): A method for handling responses.
        """
        self.components[component_name] = (process_request_method, process_response_method)
        logger.debug(f"Component '{component_name}' registered with dispatcher.")

    @pyqtSlot(dict)
    def dispatch_request(self, params: dict) -> None:
        """Dispatch a request to the appropriate component.

        Args:
            params (dict): The parameters of the request, must include 'target' to identify the component.
        """
        target = params.get("target")
        if target in self.components:
            process_request_method, _ = self.components[target]
            process_request_method(params)
        else:
            logger.error(f"No component found for target '{target}'")

    @pyqtSlot(dict)
    def dispatch_response(self, params: dict) -> None:
        """Dispatch a response to the appropriate component.

        Args:
            params (dict): The parameters of the response, must include 'target' to identify the component.
        """
        target = params.get("target")
        if target in self.components:
            _, process_response_method = self.components[target]
            process_response_method(params)
        else:
            logger.error(f"No component found for target '{target}'")


class BasicSignals(QObject):
    """A base class providing a request/response mechanism via signals and an event loop.

    This class serves as a basic abstraction for sending requests to other
    registered components and waiting for responses. It uses QEventLoop to
    block until a response is received or until a timeout occurs.
    """

    def __init__(self, actor_name: str, dispatcher: SignalDispatcher):
        """Initialize BasicSignals.

        Args:
            actor_name (str): The name of the actor (component).
            dispatcher (SignalDispatcher): The dispatcher used to send requests and receive responses.

        Raises:
            ValueError: If actor_name is not provided.
        """
        super().__init__()
        if not actor_name:
            raise ValueError("actor_name must be provided for BasicSignals.")
        self.actor_name = actor_name
        self.dispatcher = dispatcher
        self.pending_requests: Dict[str, Dict[str, Any]] = {}
        self.event_loops: Dict[str, QEventLoop] = {}
        self.dispatcher.register_component(self.actor_name, self.process_request, self.process_response)

    def connect_to_dispatcher(self) -> None:
        """Connects to the dispatcher signals for handling requests and responses."""
        self.dispatcher.request_signal.connect(self.process_request)
        self.dispatcher.response_signal.connect(self.process_response)
        logger.debug(f"{self.actor_name} connected to dispatcher signals.")

    def handle_request_cycle(self, target: str, operation: str, **kwargs) -> Any:
        """Create a request, send it, and wait for the response.

        Args:
            target (str): The target system for the request.
            operation (str): The operation to be performed.
            **kwargs: Additional parameters for the request.

        Returns:
            Any: The response data if successful, otherwise None.
        """
        request_id = self.create_and_emit_request(target, operation, **kwargs)
        response_data = self.handle_response_data(request_id, operation)
        if response_data is not None:
            return response_data
        else:
            logger.error(f"{self.actor_name}_handle_request_cycle: {operation} completed with None")
            return None

    def create_and_emit_request(self, target: str, operation: str, **kwargs) -> str:
        """Create and emit a request signal.

        Args:
            target (str): The target system for the request.
            operation (str): The operation to be performed.
            **kwargs: Additional parameters for the request.

        Returns:
            str: The unique request ID for this request.
        """
        request_id = str(uuid.uuid4())
        self.pending_requests[request_id] = {"received": False, "data": None}
        request = {
            "actor": self.actor_name,
            "target": target,
            "operation": operation,
            "request_id": request_id,
            **kwargs,
        }
        logger.debug(f"{self.actor_name} is emitting request: {request}")
        self.dispatcher.request_signal.emit(request)
        return request_id

    def process_request(self, params: dict) -> None:
        """Process an incoming request.

        This method should be overridden in subclasses to provide specific request handling logic.

        Args:
            params (dict): The request parameters.
        """
        pass

    def process_response(self, params: dict) -> None:
        """Process an incoming response.

        Args:
            params (dict): The response parameters, must contain 'request_id' and 'operation'.
        """
        if params.get("target") != self.actor_name:
            return
        logger.debug(f"{self.actor_name} will process response:\n{params=}")
        request_id = params.get("request_id")
        operation = params.get("operation")
        if request_id in self.pending_requests:
            self.pending_requests[request_id]["data"] = params
            self.pending_requests[request_id]["received"] = True
            if request_id in self.event_loops:
                self.event_loops[request_id].quit()
        else:
            logger.error(f"{self.actor_name}_response_slot: unknown operation='{operation}' UUID: {request_id}")

    def wait_for_response(self, request_id: str, timeout: int = 1000) -> Optional[dict]:
        """Wait for a response to a specific request.

        Args:
            request_id (str): The ID of the request.
            timeout (int, optional): The time to wait in milliseconds. Defaults to 1000.

        Returns:
            Optional[dict]: The response data if received in time, otherwise None.
        """
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
                f"{self.actor_name}_wait_for_response: {request_id} waiting time has expired\n"
                f"waiting is stopped: {self.event_loops.get(request_id, None) is None}"
            )
            return None
        return self.pending_requests.pop(request_id)["data"]

    def handle_response_data(self, request_id: str, operation: str) -> Any:
        """Handle the response data for a given request ID.

        Args:
            request_id (str): The request ID associated with the response.
            operation (str): The requested operation.

        Returns:
            Any: The response data if available, otherwise None.
        """
        response_data = self.wait_for_response(request_id)
        if response_data is not None:
            return response_data.pop("data", None)
        else:
            logger.error(f"{self.actor_name}_handle_response: {operation} waiting time has expired")
            return None
