import os
import subprocess
import re
from typing import Optional, Callable, List
from dataclasses import dataclass

from status import parse
from brother_ql.backends import backend_factory, BrotherQLBackendGeneric


@dataclass
class PrinterInfo:
    serial: str
    path: str


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
            return handle.read()
    return None


def detect_printers() -> List[PrinterInfo]:
    info = []
    accessor = backend_factory("linux_kernel")
    devices = accessor['list_available_devices']()
    # backend_class = accessor['backend_class']

    for device in devices:
        identifier = device['identifier']
        result = try_get_serial(identifier)
        info.append(PrinterInfo(serial=result, path=identifier))
        print(f"{identifier} has serial {result}")

    return info

        #
        # backend = backend_class(device['identifier'])
        # backend.write(b'\x1B\x69\x53')
        # data = attempt_read(backend)
        # if data:
        #     parse(data)
        #     print(" ".join(f"{int(b):x}" for b in data))


# def attempt_read(backend: BrotherQLBackendGeneric):
#     attempts = 0
#     while attempts < 5:
#         result = backend.read()
#         if result:
#             return result
#         attempts += 1


def main():
    detect_printers()


if __name__ == '__main__':
    main()