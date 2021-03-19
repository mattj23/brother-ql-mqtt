import os
import time
import rx
import json
import socket
from paho.mqtt.client import Client

from printer import detect_printers

host_name = socket.gethostname()

is_running = True


def get_host_ip():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.connect(('10.0.0.0', 1))
            return s.getsockname()[0]
        except Exception:
            return '127.0.0.1'


def on_message(client: Client, user_data, message):
    global is_running
    print(message)


def on_connect(client: Client, user_data, flags, rc):
    print(f"Connected with result code {rc}")
    sub_topic = f"label_server/print/{host_name}"
    print(f"Subscribing to: {sub_topic}")
    client.subscribe(sub_topic)


def main():
    client = Client(host_name)
    client.connect("abacus.mjarvis.info", 1883, 60)
    client.on_connect = on_connect
    client.on_message = on_message

    client.loop_start()

    while is_running:
        time.sleep(5)
        ip_address = get_host_ip()
        printers = detect_printers()
        status = {
            "ip": ip_address,
            "printers": [p.serial for p in printers]
        }
        client.publish(f"label_servers/status/{host_name}", json.dumps(status))


if __name__ == '__main__':
    main()
