import logging
from mxcubecore.HardwareObjects import BeamInfo
from mxcubecore.HardwareObjects.abstract import AbstractBeam
from mxcubecore import HardwareRepository as HWR
from enum import Enum, unique

"""
XML example file
<object class="MAXIV:MicroMAX.MICROMAXBeamInfo">
  <defaultBeamDivergence></defaultBeamDivergence>
  <device role="camera" hwrid="/prosilica_md2"/>
  <device role="aperture" hwrid="/udiff_aperturemot"/>
  <device role="diffractometer" hwrid="/udiff" />
  <!-- Positions and slits format: X Y -->
  <beam_position>322 243</beam_position>
  <beam_size_slits>0.04 0.04</beam_size_slits>
  <beam_divergence_vertical>6.5</beam_divergence_vertical>
  <beam_divergence_horizontal>104</beam_divergence_horizontal>
</object>
"""


@unique
class BeamShape(Enum):
    """Beam shape definitions"""

    UNKNOWN = "unknown"
    RECTANGULAR = "rectangular"
    ELIPTICAL = "ellipse"


@unique
class HardwareObjectState(Enum):
    """Enumeration of common states, shared between all HardwareObjects"""

    # probably since BeamInfo inherits from Equipment
    UNKNOWN = 0
    WARNING = 1
    BUSY = 2
    READY = 3
    FAULT = 4
    OFF = 5


class MICROMAXBeamInfo(BeamInfo.BeamInfo, AbstractBeam.AbstractBeam):
    def __init__(self, *args):
        BeamInfo.BeamInfo.__init__(self, *args)
        self.beam_position = (0, 0)
        self._beam_width = None
        self._beam_height = None
        self._beam_shape = None
        self._beam_label = None
        self._beam_divergence = (None, None)
        self._beam_position_on_screen = [None, None]  # TODO move to sample_view

    def init(self):
        self.chan_beam_size_microns = None
        self.chan_beam_shape_ellipse = None
        BeamInfo.BeamInfo.init(self)
        beam_size_slits = self.get_property("beam_size_slits")
        if beam_size_slits:
            self.beam_size_slits = tuple(map(float, beam_size_slits.split()))

        self._aperture = self.get_object_by_role("aperture")
        if self._aperture is not None:
            self.connect(self._aperture, "valueChanged", self.aperture_pos_changed)
        else:
            logging.getLogger("HWR").debug("BeamInfo: Aperture hwobj not defined")

        beam_position = self.get_property("beam_position")
        if beam_position:
            self._beam_position_on_screen = tuple(map(float, beam_position.split()))
        else:
            logging.getLogger("HWR").warning(
                "MICROMAXBeamInfo: " + "beam position not configured"
            )
        self.difrractometer_hwobj = self.get_object_by_role("difrractometer")

    def get_beam_position(self):
        if self.beam_position == (0, 0):
            try:
                self.beam_position = HWR.beamline.diffractometer.beam.get_value()
            except AttributeError:
                self.beam_position = (
                    HWR.beamline.sample_view.camera.get_width() / 2,
                    HWR.beamline.sample_view.camera.get_height() / 2,
                )
        return self.beam_position

    def set_beam_position(self, beam_x, beam_y):
        return

    def evaluate_beam_info(self, *args):
        self.beam_info_dict["shape"] = "ellipse"
        current_aperture = float(self._aperture.get_diameter_size())
        self._beam_width = current_aperture / 1000
        self.beam_info_dict["size_x"] = self._beam_width
        self._beam_height = current_aperture / 1000
        self.beam_info_dict["size_y"] = self._beam_height
        return self.beam_info_dict

    def get_value(self):
        pos = self.get_beam_position()
        current_aperture = float(self._aperture.get_diameter_size()) / 1000

        return current_aperture, current_aperture, BeamShape.ELIPTICAL, current_aperture

    def set_value(self, value):
        self._aperture.set_diameter_size(value)

    def get_available_size(self):
        """Get the available predefined beam definers configuration.
        Returns:
            (dict): Dictionary {"type": (list), "values": (list)}, where
               "type": the definer type
               "values": List of available beam size definitions,
                         according to the "type".
        """
        aperture_list = self._aperture.get_diameter_size_list()
        return {"type": ["enum"], "values": aperture_list}

    def get_state(self):
        """Getter for state attribute

        Implementations must query the hardware directly, to ensure current results

        Returns:
            HardwareObjectState
        """
        return HardwareObjectState.READY
