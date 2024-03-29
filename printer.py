import os
import subprocess
import re
import time
from abc import ABCMeta, abstractmethod
from datetime import timedelta
from typing import Optional, Dict

import brother_ql.brother_ql_create

from common import PrinterInfo, PhaseState
from status import get_status, Status, parse, attempt_read, StatusType
from brother_ql import BrotherQLRaster
from brother_ql.backends import backend_factory

from PIL import Image

from rx.scheduler import EventLoopScheduler

import logging

logger = logging.getLogger(__name__)


class PrinterBase(metaclass=ABCMeta):
    @abstractmethod
    def __init__(self, serial: str):
        self.serial = serial

    @abstractmethod
    def print_image(self, image: Image, red: bool = False):
        pass

    @abstractmethod
    def dispose(self):
        pass

    @abstractmethod
    def info(self):
        pass


class MockPrinter(PrinterBase):
    def __init__(self, serial: str):
        self.serial = serial
        self.model = "Mock Printer"

        self.status = Status(model="MOCK PRINTER",
                             media_width=62,
                             media_length=0,
                             media_type="Continuous",
                             errors=0,
                             status_type=StatusType.PhaseChange,
                             phase=PhaseState.Receiving,
                             notification=0)

    def print_image(self, image: Image, red = False):
        logger.debug(f"Mock printing image data")

    def dispose(self):
        pass

    def info(self):
        return PrinterInfo(model=self.model, serial=self.serial, status=self.status)


class Printer(PrinterBase):
    def __init__(self, path: str, serial: str, check_period: int = 5):
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
        print_data = brother_ql.brother_ql_create.convert(raster, [image], str(self.label_width), dither=True)
        self.backend.write(print_data)
        start = time.time()
        while True:
            data = attempt_read(self.backend)
            if data:
                self.status = parse(data)
                print(self.status)

                if self.status.status_type == StatusType.ErrorOccurred:
                    logger.info(f"Error occurred while printing {self.serial}")
                    break

                if self.status.status_type == StatusType.PrintingComplete:
                    break

            time.sleep(0.2)

            if time.time() - start > 3:
                logger.info(f"Status timeout while printing on {self.serial}")
                break

        # send initialize
        self.backend.write(b'\x1b\x40')

        del raster

    def dispose(self):
        logger.debug(f"Disposing of {self.serial}")
        self.periodic.dispose()

    def info(self) -> PrinterInfo:
        return PrinterInfo(model=self.model, serial=self.serial, status=self.status)


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
