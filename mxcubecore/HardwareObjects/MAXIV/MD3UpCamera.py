"""
Camera hardware object for Arinax MD3UP on-axis video microscope.

Implements the required API for displaying MD3UP microscope video stream in the UI.

Supported properties:

  tangoname (required) - name or full URL of the Arinax tango video device
  interval - frame polling interval, in milliseconds
"""
from pathlib import Path
from io import BytesIO
import struct
import gevent
import uuid
import time
import PyTango
from PIL import Image
from mxcubecore.BaseHardwareObjects import HardwareObject

# default polling interval for video frames, in milliseconds
DEFAULT_POLL_INTERVAL = 50  # ~20 FPS

# monochrome, 8-bit per pixel
IMAGE_MODE_L = 0
# rgb, 24-bit per pixel
IMAGE_MODE_RGB = 6


class MD3UpCamera(HardwareObject):
    def __init__(self, name):
        super().__init__(name)
        self.stream_hash = str(uuid.uuid1())
        self.device = None
        self._poll_images = False
        self._start_polling = gevent.event.Event()

    def init(self):
        # calculate polling interval in seconds
        self._poll_interval = (
            self.get_property("interval", DEFAULT_POLL_INTERVAL) / 1000
        )
        self.device = PyTango.DeviceProxy(self.get_property("tangoname"))
        self.device.ping()
        gevent.spawn(self._poll)

    def get_image_zoom(self):
        # hard-coded to 1.0, for compatibility reasons
        return 1.0

    def get_width(self):
        return self.device.image_width

    def get_height(self):
        return self.device.image_height

    def connect_notify(self, signal):
        if signal != "imageReceived":
            # we only care about 'imageReceived' signal connections
            return

        # video client connected, start fetching images from MD3Up
        self._poll_images = True
        self._start_polling.set()

    def disconnect_notify(self, signal):
        if signal != "imageReceived":
            # we only care about 'imageReceived' signal connections
            return

        # video client disconnected, stop fetching images
        self._poll_images = False

    def _get_frame(self):
        """
        read one frame from tango device

        returns: frame's width, height, color mode and pixels,
        """
        _, frame = self.device.video_last_image

        (
            magic_number,
            version,
            image_mode,
            frame_number,
            width,
            height,
            endianness,
            header_size,
        ) = struct.unpack(">IHHqiiHH", frame[0:28])

        #
        # The MD3Up will give us images either in RGB24 format or
        # in Monochrome 8-bit format, depending on the zoom level.
        #
        # This function maps LIMA image mode numbers to PIL image format
        # names, so that we can convert both of the images to a JPEG image.
        #

        if image_mode == IMAGE_MODE_RGB:
            return width, height, "RGB", frame[header_size:]

        # should be image in monochrome 8-bit format
        assert image_mode == IMAGE_MODE_L

        # the MD3UP tango device sends some extra bytes when in the monochrome mode,
        # we need to cut them off
        end = header_size + (width * height)
        return width, height, "L", frame[header_size:end]

    def _get_jpg_image(self):
        """
        get one frame from tango device and encode it as jpeg
        """
        width, height, mode, pixels = self._get_frame()

        image = Image.frombytes(mode, (width, height), pixels)

        buffer = BytesIO()
        image.save(buffer, "JPEG")

        jpg_img = buffer.getvalue()
        return width, height, jpg_img

    def _poll(self):
        def fetch_images():
            while self._poll_images:
                width, height, jpg_img = self._get_jpg_image()
                self.emit("imageReceived", jpg_img, width, height)
                time.sleep(self._poll_interval)

        while True:
            self._start_polling.wait()
            self._start_polling.clear()
            fetch_images()
