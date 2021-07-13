import os
import subprocess
import re
import time
from datetime import timedelta
from typing import Optional, Callable, List, Dict
from dataclasses import dataclass

import brother_ql.brother_ql_create

from status import get_status, Status, parse, attempt_read, StatusType
from brother_ql import brother_ql_create, BrotherQLRaster
from brother_ql.backends import backend_factory, BrotherQLBackendGeneric, helpers

from PIL import Image

from rx.scheduler import EventLoopScheduler

import logging

logger = logging.getLogger(__name__)


class Printer:
    def __init__(self, path: str, serial: str, check_period: int=5):
        self.path = path
        self.serial = serial
        self.backend_cls = backend_factory("linux_kernel")['backend_class']
        self.backend = self.backend_cls(self.path)
        self.model: Optional[str] = None
        self.scheduler = EventLoopScheduler()
        self.status: Optional[Status] = None
        self.label_width: Optional[int] = None

        self.periodic = self.scheduler.schedule_periodic(timedelta(seconds=check_period), self._get_status)

    def _get_status(self, state):
        logger.debug("Getting status")

        try:
            self.status = get_status(self.backend)
            self.model = self.status.model
            self.label_width = self.status.media_width
        except:
            self.status = None

    def print_image(self, image: Image, red=False):
        raster = BrotherQLRaster(self.model)
        print_data = brother_ql.brother_ql_create.convert(raster, [image], str(self.label_width), dither=True, red=red)
        self.backend.write(print_data)
        while True:
            data = attempt_read(self.backend)
            if data:
                start = time.time()
                self.status = parse(data)
                print(self.status)

                if self.status.status_type == StatusType.ErrorOccurred:
                    logger.info(f"Error occurred while printing {self.serial}")
                    break

                if self.status.status_type == StatusType.PrintingComplete:
                    break

            time.sleep(0.2)

        # send initialize
        self.backend.write(b'\x1b\x40')

        del raster

    def dispose(self):
        logger.debug(f"Disposing of {self.serial}")
        self.periodic.dispose()

    def info_dict(self) -> Dict:
        info = {"model": self.model, "serial": self.serial, "status": None}
        if self.status is not None:
            info["status"] = self.status.as_dict()
        return info


def try_get_serial(identifier: str) -> Optional[str]:
    """ Attempt to get the serial number of a device name path via the pseudo-filesystem in /sys/devices. This will
    obviously only work on linux and it requires udevadm be installed and accessible. """
    path_pattern = re.compile(r"DEVPATH=/(.+)\n")
    if identifier.startswith("file://"):
        identifier = identifier.replace("file://", "")

    process = subprocess.Popen(["udevadm", "info", f"--name={identifier}"], stdout=subprocess.PIPE)
    result, _ = process.communicate()
    dev_path = path_pattern.findall(result.decode())
    working_folder = os.path.abspath(os.path.join("/sys", dev_path[0]))
    while ":" not in os.path.basename(working_folder):
        working_folder = os.path.abspath(os.path.join(working_folder, ".."))
    working_folder = os.path.abspath(os.path.join(working_folder, ".."))
    serial_file = os.path.join(working_folder, "serial")
    if os.path.exists(serial_file):
        with open(serial_file, "r") as handle:
            return handle.read().strip()
    return None


def detect_printers() -> Dict[str, str]:
    info = {}
    accessor = backend_factory("linux_kernel")
    devices = accessor['list_available_devices']()

    for device in devices:
        identifier = device['identifier']
        result = try_get_serial(identifier)
        info[result] = identifier

    return info


def main():
    detect_printers()


if __name__ == '__main__':
    main()
