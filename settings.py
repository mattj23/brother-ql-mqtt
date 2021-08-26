import json
import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class Settings:
    mqtt_broker_host: str
    mqtt_broker_port: int
    printer_check_period_s: Optional[int] = 5
    status_update_period_s: Optional[int] = 5
    tls_cafile: Optional[str] = None


def load_settings():
    target_file = "settings.dev.json" if os.path.exists("settings.dev.json") else "settings.json"

    with open(target_file, "r") as handle:
        return Settings(**json.load(handle))
