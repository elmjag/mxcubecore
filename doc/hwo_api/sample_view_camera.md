# HWR.beamline.sample_view.camera

Implements video feed of the mounted sample on the gonio.
This is the sample view video shown in the UI.
It is typically video feed of the diffractometer's on-axis microscope.

_required methods_

| signature                      | returns                |
|--------------------------------|------------------------|
| \_\_init\_\_(self, name: str)  |                        |
| get_width(self)                | int                    |
| get_height(self)               | int                    |
| take_snapshot(self, path, ???) |                        |

_expected signals_

| name          | payload                               |
|---------------|---------------------------------------|
| imageReceived | image: bytes, width: int, height:int  |

## Methods

### \_\_init\_\_(self, name: str)

The object's will be created by invoking a constractor with above signature.

`name`: object's name in the configuration files

### get_width(self) -> int:

Should return width, in pixels, of the video frame.

### get_height(self) -> int:

Should return height, in pixels, of the video frame.

### take_snapshot(self, path, ???):

???

## Signals

### imageReceived

This object should emit a `globalStateChanged` signal when a new frame is available.
The expected signal's payload is:

* `frame` : the new frame, as bytes, encoded as jpeg image
* `width`: frame's width in pixels
* `height`: : frame's height in pixels
