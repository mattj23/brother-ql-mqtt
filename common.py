import json
import os
from enum import Enum
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, List, Callable
from abc import ABC


class RequestMode(Enum):
    PNG = 0
    URL = 1

    @staticmethod
    def parse(text: str):
        lowered = text.lower()
        if lowered == "png":
            return RequestMode.PNG
        elif lowered == "url":
            return RequestMode.URL
        raise ValueError(f"Could not convert '{text}' to a RequestMode, must be 'png' or 'url'")


@dataclass
class PrintRequest:
    serial: str
    mode: RequestMode
    payload: Any


class StatusType(Enum):
    Reply = 0x0
    PrintingComplete = 0x1
    ErrorOccurred = 0x2
    TurnedOff = 0x4
    Notification = 0x5
    PhaseChange = 0x6


class PhaseState(Enum):
    Receiving = 0x0
    Printing = 0x1


@dataclass
class Status:
    model: str
    media_width: int
    media_length: int
    media_type: str
    errors: int
    status_type: StatusType
    phase: PhaseState
    notification: int

    def as_dict(self):
        temp = asdict(self)
        temp["status_type"] = str(self.status_type)
        temp["phase"] = str(self.phase)
        return temp


@dataclass
class PrinterInfo:
    model: str
    serial: str
    status: Optional[Status]

    def as_dict(self):
        temp = asdict(self)
        temp["status"] = self.status.as_dict()
        return temp


@dataclass
class HostStatus:
    online: bool
    ip: str
    host: str
    update_s: float
    printers: List[PrinterInfo]

    def as_dict(self):
        temp = asdict(self)
        temp["printers"] = [p.as_dict() for p in self.printers]
        return temp


class TransportClient(ABC):
    def publish(self, status: HostStatus):
        pass

    def start(self, on_message: Callable[[PrintRequest], None]):
        pass


@dataclass
class SignalRSettings:
    endpoint: str
    verify_ssl: bool = True


@dataclass
class MqttSettings:
    mqtt_broker_host: str
    mqtt_broker_port: int
    tls_cafile: Optional[str] = None


@dataclass
class Settings:
    mode: str
    printer_check_period_s: Optional[int] = 5
    status_update_period_s: Optional[int] = 5
    mqtt: Optional[MqttSettings] = None
    signalr: Optional[SignalRSettings] = None


def load_settings() -> Settings:
    target_file = "settings.dev.json" if os.path.exists("settings.dev.json") else "settings.json"

    with open(target_file, "r") as handle:
        settings_dict: Dict = json.load(handle)
        mode = settings_dict.get("mode")
        if mode not in ["mqtt", "signalr"]:
            raise Exception("The 'mode' flag in the settings need to be either 'mqtt' or 'signalr'")

        settings = Settings(**settings_dict)

        if mode == "mqtt":
            settings.mqtt = MqttSettings(**settings_dict["mqtt"])
            settings.signalr = None
        elif mode == "signalr":
            settings.mqtt = None
            settings.signalr = SignalRSettings(**settings_dict["signalr"])
        else:
            raise Exception("Settings load error")

        return settings
