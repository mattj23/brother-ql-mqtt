import sys
import logging
from typing import Dict

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s [%(levelname)s] %(message)s")
logger = logging.getLogger()

import time
import rx
import json
import socket
from paho.mqtt.client import Client, MQTTMessage

from printer import detect_printers, Printer
from print_manager import PrintManager
from settings import Settings, load_settings

host_name = socket.gethostname()
is_running = True
printers: Dict[str, Printer] = {}
managers: Dict[str, PrintManager] = {}
sub_topic_root = f"label_servers/print/{host_name}"


def get_host_ip():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.connect(('10.0.0.0', 1))
            return s.getsockname()[0]
        except Exception:
            return '127.0.0.1'


def on_message(client: Client, user_data, message: MQTTMessage):
    logger.info(f"Received Message: {message.topic}")

    # Remove topic root
    stripped = message.topic.replace(sub_topic_root, "").strip("/")

    # Print requests should be of the form "<printer_serial>/<mode>"
    parts = stripped.split("/")
    if len(parts) >= 2 and parts[0] in printers:
        serial, mode, *_ = parts
        managers[serial].handle_request(mode, message.payload)


def on_connect(client: Client, user_data, flags, rc):
    logger.info(f"Connected with result code {rc}")
    sub_topic = f"{sub_topic_root}/#"
    logger.info(f"Subscribing to: {sub_topic}")
    client.subscribe(sub_topic)


def update_known_printers(settings: Settings):
    """ Detect the printers currently on the system and update the printers dictionary as appropriate. """
    detected = detect_printers()
    for serial, path in detected.items():
        if serial not in printers:
            logger.info(f"Adding printer {serial}")
            printers[serial] = Printer(path=path, serial=serial, check_period=settings.printer_check_period_s)
            managers[serial] = PrintManager(printers[serial])

    for k in list(printers.keys()):
        if k not in detected:
            logger.info(f"Removing printer {k}")
            printers[k].dispose()
            del printers[k]
            del managers[k]


def main():
    logger.info(f"Starting server")

    settings = load_settings()

    client = Client(host_name)
    client.connect(settings.mqtt_broker_host, settings.mqtt_broker_port, 60)
    client.on_connect = on_connect
    client.on_message = on_message

    client.loop_start()

    while is_running:
        ip_address = get_host_ip()
        update_known_printers(settings)

        status = {
            "ip": ip_address,
            "host": host_name,
            "printers": [p.info_dict() for k, p in printers.items()]
        }
        client.publish(f"label_servers/status/{host_name}", json.dumps(status))
        time.sleep(5)


if __name__ == '__main__':
    main()
