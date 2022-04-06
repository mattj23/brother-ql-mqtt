import base64
import json
import time
from typing import Any, Optional, Callable

from signalrcore.hub.errors import HubConnectionError

from common import TransportClient, HostStatus, PrintRequest, SignalRSettings, RequestMode
from signalrcore.hub_connection_builder import HubConnectionBuilder, BaseHubConnection

import logging

logger = logging.getLogger(__name__)


class SignalRClient(TransportClient):
    def __init__(self, settings: SignalRSettings):
        self.settings = settings
        self._callback: Optional[Callable[[PrintRequest], Any]] = None

        self._connected = False

        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG)

        self.connection: BaseHubConnection = HubConnectionBuilder() \
            .with_url(self.settings.endpoint, options={"verify_ssl": self.settings.verify_ssl}) \
            .configure_logging(logging.DEBUG, socket_trace=True, handler=handler) \
            .with_automatic_reconnect({"type": "raw", "reconnect_interval": 10, "keep_alive_interval": 10}) \
            .build()
        self.connection.on_open(self._on_connected)
        self.connection.on_close(self._on_disconnected)

        self.connection.on("SendPrintRequest", self._on_receive_request)

    def _on_connected(self):
        self._connected = True
        logger.info("Connected to SignalR hub established")

    def _on_disconnected(self):
        self._connected = False
        logger.info("Disconnected from SignalR hub")

    def _on_receive_request(self, request):
        serial, mode_, payload = request
        mode = RequestMode(mode_)
        if mode == RequestMode.PNG:
            payload = base64.b64decode(payload)
        if self._callback:
            self._callback(PrintRequest(serial, mode, payload))

    def publish(self, status: HostStatus):
        if not self.connection:
            return

        try:
            self.connection.send("ReceivePrinterInfo", [json.dumps(status.as_dict())])
        except HubConnectionError:
            logger.info("SignalR Hub is not responding")

    def start(self, on_message: Callable[[PrintRequest], None]):
        self._callback = on_message
        self.connection.start()
        time.sleep(1)
