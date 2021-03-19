import sys
import logging
from typing import Dict

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s [%(levelname)s] %(message)s")
logger = logging.getLogger()

import time
import rx
import json
import socket
from paho.mqtt.client import Client

from printer import detect_printers, Printer


host_name = socket.gethostname()
is_running = True
printers: Dict[str, Printer] = {}

def get_host_ip():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.connect(('10.0.0.0', 1))
            return s.getsockname()[0]
        except Exception:
            return '127.0.0.1'


def on_message(client: Client, user_data, message):
    logger.info(f"Rx Message")
    print(message)


def on_connect(client: Client, user_data, flags, rc):
    logger.info(f"Connected with result code {rc}")
    sub_topic = f"label_server/print/{host_name}"
    logger.info(f"Subscribing to: {sub_topic}")
    client.subscribe(sub_topic)


def update_known_printers():
    """ Detect the printers currently on the system and update the printers dictionary as appropriate. """
    detected = detect_printers()
    for serial, path in detected.items():
        if serial not in printers:
            logger.info(f"Adding printer {serial}")
            printers[serial] = Printer(path=path, serial=serial)

    for k in list(printers.keys()):
        if k not in detected:
            logger.info(f"Removing printer {k}")
            printers[k].dispose()
            del printers[k]


def main():
    logger.info(f"Starting server")
    client = Client(host_name)
    client.connect("abacus.mjarvis.info", 1883, 60)
    client.on_connect = on_connect
    client.on_message = on_message

    client.loop_start()

    while is_running:
        ip_address = get_host_ip()
        update_known_printers()

        status = {
            "ip": ip_address,
            # "printers": [p.serial for p in printers]
        }
        client.publish(f"label_servers/status/{host_name}", json.dumps(status))
        time.sleep(5)


if __name__ == '__main__':
    main()
