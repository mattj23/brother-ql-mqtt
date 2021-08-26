import time
from enum import Enum
from typing import Optional
from dataclasses import dataclass, asdict

from brother_ql.backends import BrotherQLBackendGeneric

models = {
    0x3431: "QL-560",
    0x3432: "QL-570",
    0x3433: "QL-580N",
    0x3434: "QL-1060N",
    0x3435: "QL-700",
    0x3436: "QL-710W",
    0x3437: "QL-720NW",
    0x3438: "QL-800",
    0x3439: "QL-810W",
    0x3441: "QL-820NWB",
    0x3443: "QL-1100",
    0x3444: "QL-1110NWB",
    0x3445: "QL-1115NWB",
    0x3447: "QL-600",
}

media_types = {
    0x00: "Empty",
    0xFF: "Incompatible",
    0x0A: "Continuous",
    0x0B: "Die-cut",
    0x4A: "Continuous",
    0x4B: "Die-cut",
}


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


def get_status(backend: BrotherQLBackendGeneric) -> Optional[Status]:
    backend.write(b'\x1B\x69\x53')
    data = attempt_read(backend)
    if data:
        return parse(data)
    return None


def attempt_read(backend: BrotherQLBackendGeneric):
    attempts = 0
    while attempts < 5:
        time.sleep(0.1)
        result = backend.read()
        if result:
            return result
        attempts += 1


def parse(b: bytes) -> Status:
    # print(" ".join(f"{int(b_):x}" for b_ in b))
    model_code = int.from_bytes(b[3:5], "big")
    errors = int.from_bytes(b[8:10], "big")
    media_width = int(b[10])
    media_type = int(b[11])
    media_length = int(b[17])
    status_type = int(b[18])
    phase = int(b[19])
    notification = int(b[22])
    text_color = int(b[25])

    # print(f"0x{text_color:x}")
    return Status(
        model=models.get(model_code, "Unknown"),
        media_width=media_width,
        media_length=media_length,
        media_type=media_types.get(media_type, "Unknown"),
        errors=errors,
        status_type=StatusType(status_type),
        phase=PhaseState(phase),
        notification=notification
    )
