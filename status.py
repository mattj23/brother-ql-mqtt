

class Status:
    def __init__(self):
        pass



def parse(b: bytes):
    model_code = int.from_bytes(b[3:5], "big")
    errors = int.from_bytes(b[8:10], "big")
    media_width = int(b[10])
    media_type = int(b[11])
    status_type = int(b[18])
    notification = int(b[22])
    text_color = int(b[25])

    print(f"0x{text_color:x}")