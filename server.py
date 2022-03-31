import sys
import logging
from typing import Dict, Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s [%(levelname)s] %(message)s")
logger = logging.getLogger()

import time
import json
import socket

from printer import detect_printers, Printer
from print_manager import PrintManager
from common import Settings, load_settings, TransportClient, HostStatus, PrintRequest
from mqtt_client import MqttClient

host_name = socket.gethostname()
is_running = True
printers: Dict[str, Printer] = {}
managers: Dict[str, PrintManager] = {}


def get_host_ip():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.connect(('10.0.0.0', 1))
            return s.getsockname()[0]
        except Exception:
            return '127.0.0.1'


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


def on_request_receive(request: PrintRequest):
    if request.serial in managers:
        managers[request.serial].handle_request(request)
    else:
        logger.info(f"Request for {request.serial}, a printer which was not found")


def main():
    logger.info(f"Starting server")

    settings = load_settings()

    client: Optional[TransportClient] = None
    if settings.mqtt:
        client = MqttClient(host_name, settings.mqtt)

    if not client:
        raise Exception("No transport client was created")

    client.start(on_request_receive)

    while is_running:
        ip_address = get_host_ip()
        update_known_printers(settings)

        status = HostStatus(online=True, ip=ip_address, host=host_name, update_s=settings.printer_check_period_s,
                            printers=[p.info() for p in printers.values()])
        client.publish(status)
        time.sleep(settings.printer_check_period_s)


if __name__ == '__main__':
    main()
