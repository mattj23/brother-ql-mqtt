import json
from typing import Any, Optional, Callable

from common import TransportClient, HostStatus, PrintRequest, MqttSettings, RequestMode
from paho.mqtt.client import Client, MQTTMessage

import logging

logger = logging.getLogger(__name__)


class MqttClient(TransportClient):
    def __init__(self, host_name: str, settings: MqttSettings):
        self.host_name = host_name
        self.settings = settings
        self.sub_topic_root = f"label_servers/print/{host_name}"
        self._callback: Optional[Callable[[PrintRequest], Any]] = None

        # Configure the client
        self.client = Client(self.host_name)

        # TLS settings if we have them
        if self.settings.tls_cafile is not None and self.settings.tls_cafile.strip():
            self.client.tls_set(self.settings.tls_cafile)

        self.client.connect(settings.mqtt_broker_host, settings.mqtt_broker_port, 60)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message

    def _on_connect(self, client: Client, user_data, flags, reason_code, properties=None):
        logger.info(f"Connected with reason code {reason_code}")

        sub_topic = f"{self.sub_topic_root}/#"
        logger.info(f"Subscribing to: {sub_topic}")
        client.subscribe(sub_topic)
        client.will_set(f"label_servers/status/{self.host_name}", json.dumps({"online": False}))

    def _on_message(self, client: Client, user_data, message: MQTTMessage):
        logger.info(f"Received Message: {message.topic}")

        try:
            # Remove topic root
            stripped = message.topic.replace(self.sub_topic_root, "").strip("/")

            # Print requests should be of the form "<printer_serial>/<mode>"
            parts = stripped.split("/")
            if len(parts) >= 2:
                serial, mode, *_ = parts
                request = PrintRequest(serial, RequestMode.parse(mode), message.payload)
                if self._callback:
                    self._callback(request)
        except Exception as e:
            logger.error("Error processing received message", exc_info=e)

    def publish(self, status: HostStatus):
        self.client.publish(f"label_servers/status/{self.host_name}",
                            json.dumps(status.as_dict()))

    def start(self, on_message: Callable[[PrintRequest], None]):
        self._callback = on_message
        self.client.loop_start()
