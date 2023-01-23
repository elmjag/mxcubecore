"""
Camera hardware object for Arinax MD3UP on-axis video microscope.

Implements the required API for displaying MD3UP microscope video stream in the UI.

Supported properties:

  tangoname (required) - name or full URL of the Arinax tango video device
  interval - frame polling interval, in milliseconds
"""

import logging
import struct
import subprocess
import time
from io import BytesIO
from pathlib import Path
from typing import (
    List,
    Literal,
    Tuple,
)

import gevent
import psutil
import tango
from PIL import Image

from mxcubecore.BaseHardwareObjects import HardwareObject

log = logging.getLogger("HWR")

# default polling interval for video frames, in milliseconds
DEFAULT_POLL_INTERVAL = 50  # ~20 FPS

# monochrome, 8-bit per pixel
IMAGE_MODE_L = 0
# rgb, 24-bit per pixel
IMAGE_MODE_RGB = 6

MISSING_FRAME_WIDTH = 1224
MISSING_FRAME_HEIGHT = 1024
MISSING_FRAME_COLOR = "pink"


def _make_frame_missing_image() -> bytes:
    image = Image.new(
        "RGB", (MISSING_FRAME_WIDTH, MISSING_FRAME_HEIGHT), color=MISSING_FRAME_COLOR
    )
    buffer = BytesIO()
    image.save(buffer, "JPEG")

    return buffer.getvalue()


class MD3UpCamera(HardwareObject):
    def __init__(self, name):
        super().__init__(name)
        self.stream_hash = "md3video"
        self.device = None
        self._poll_images = False
        self._start_polling = gevent.event.Event()
        self._frame_missing_image = _make_frame_missing_image()
        self._video_stream_process = None
        self._current_stream_size = (
            0,
            0,
        )  # width, height. Property required for MPEG1 format.
        self._format = "MPEG1"
        self._port = 8000

    def init(self):
        # calculate polling interval in seconds
        self._poll_interval = (
            self.get_property("interval", DEFAULT_POLL_INTERVAL) / 1000
        )
        self.tangoname = self.get_property("tangoname")
        self.device = tango.DeviceProxy(self.tangoname)
        self.device.ping()
        self._current_stream_size = (self.get_width(), self.get_height())
        gevent.spawn(self._poll)

    def get_image_zoom(self) -> float:
        # hard-coded to 1.0, for compatibility reasons
        return 1.0

    def get_width(self) -> int:
        return self.device.image_width

    def get_height(self) -> int:
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

    def take_snapshot(self, path, grayscale=False):
        _, _, jpg_data = self._get_jpg_image()
        Path(path).write_bytes(jpg_data)

    def _get_frame(self) -> Tuple[int, int, Image.Image]:
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
            pil_mode = "RGB"
            pixels = frame[header_size:]
        else:
            # should be image in monochrome 8-bit format
            assert image_mode == IMAGE_MODE_L
            pil_mode = "L"

            # the MD3UP tango device sends some extra bytes when in the monochrome mode,
            # we need to cut them off
            end = header_size + (width * height)
            pixels = frame[header_size:end]

        image = Image.frombytes(pil_mode, (width, height), pixels)
        return width, height, image

    def _get_jpg_image(self) -> Tuple[int, int, bytes]:
        """
        get one frame from tango device and encode it as jpeg
        """
        try:
            width, height, image = self._get_frame()

            buffer = BytesIO()
            image.save(buffer, "JPEG")

            jpg_img = buffer.getvalue()
            return width, height, jpg_img
        except tango.CommunicationFailed:
            log.warning("failed to fetch video frame from MD3", exc_info=True)
            # show the user the pink 'frame is missing' image,
            # when we can't fetch latest video frame
            return MISSING_FRAME_WIDTH, MISSING_FRAME_WIDTH, self._frame_missing_image

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

    def get_available_stream_sizes(self) -> List[Tuple[int, int]]:
        """Return available video stream sizes.

        This method is required in order for mxcube to work with MPEG1 format.

        Returns:
            List[Tuple[int, int]]: List representing available video stream sizes.
        """
        try:
            width, height = self.get_width(), self.get_height()
            video_sizes = [
                (width, height),
                (width // 2, height // 2),
                (width // 4, height // 4),
            ]
            log.debug(f"MD3-UP camera {video_sizes=}")
        except (ValueError, AttributeError):
            video_sizes = []

        return video_sizes

    def get_stream_size(self) -> Tuple[int, int, float]:
        """Returns current video stream size.
        Used when video_size control is enabled in ui.yaml.

        Returns:
            Tuple[int, int, float]: Current video stream size, represented as (width, height, scale).
        """
        width, height = self._current_stream_size
        scale = float(width) / self.get_width()
        return (width, height, scale)

    def start_video_stream_process(self) -> None:
        """Start a subprocess for video streaming.
        Requires video-streamer and ffmpeg to work. Used only with external video streamer (USE_EXTERNAL_STREAMER: True in server.yml).

        """
        if (
            not self._video_stream_process
            or self._video_stream_process.poll() is not None
        ):
            self._video_stream_process = subprocess.Popen(
                [
                    "video-streamer",
                    "-uri",
                    self.tangoname.strip(),
                    "-hs",
                    "localhost",
                    "-p",
                    str(self._port),
                    "-of",
                    self._format,
                    "-q",
                    "4",
                    "-s",
                    ", ".join(map(str, self._current_stream_size)),
                    "-id",
                    self.stream_hash,
                ],
                close_fds=True,
            )

    def stop_streaming(self) -> None:
        if self._video_stream_process:
            try:
                ps = [self._video_stream_process] + psutil.Process(
                    self._video_stream_process.pid
                ).children()
                for p in ps:
                    p.kill()
            except psutil.NoSuchProcess:
                pass

            self._video_stream_process = None

    def start_streaming(
        self,
        _format: Literal["MPEG1", "MJPEG"] = "MPEG1",
        size: Tuple[int, int] = (0, 0),
        port: str = "8000",
    ) -> None:
        """Starts subprocess for streaming video from MD3UP camera.

        Required when running mxcube with external video streamer (USE_EXTERNAL_STREAMER: True) in server.yml.

        Args:
            _format: Video stream format, either "MPEG1" or "MJPEG". Defaults to "MPEG1".
            size: Video stream size in format (width, height). Defaults to (0, 0).
                Possible values are returned by self.get_available_stream_sizes().
            port: Port used by external video streamer. Defaults to "8000".
        """
        self._format = _format
        self._port = port
        if not size[0]:
            size_ = (self.get_width(), self.get_height())
        else:
            size_ = (size[0], size[1])

        self._current_stream_size = size_
        self.start_video_stream_process()

    def restart_streaming(self, size: Tuple[int, int]) -> None:
        """Restart video stream with new size.

        Used when changing video stream size in mxcube UI
        (video_size control in ui.yaml set to True, and USE_EXTERNAL_STREAMER: True in server.yml).

        Args:
            size: New size of the video stream
        """
        self.stop_streaming()
        self.start_streaming(self._format, size=size)
