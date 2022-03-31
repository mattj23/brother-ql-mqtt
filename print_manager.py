import requests

from PIL import Image
from io import BytesIO

from common import PrintRequest, RequestMode
from printer import Printer

import logging

logger = logging.getLogger(__name__)


class PrintManager:
    """
    A helper class that managers the process of taking a request for printing via some specific mode and
    turning it into an actual instruction sent to a printer object.  This might mean fetching a file from a URL or it
    could be decoding a stream of bytes into a png before sending it to the printer.
    """

    def __init__(self, printer: Printer):
        self.printer: Printer = printer

    def handle_request(self, request: PrintRequest):
        if request.mode == RequestMode.PNG:
            stream = BytesIO(request.payload)
            image = Image.open(stream, mode="r")
            self.printer.print_image(image)

        elif request.mode == RequestMode.URL:
            url = request.payload.decode()
            logger.info(f"Received URL for print on {self.printer.serial}: {url}")
            response = requests.get(url)
            stream = BytesIO(response.content)
            image = Image.open(stream, mode="r")
            self.printer.print_image(image)
