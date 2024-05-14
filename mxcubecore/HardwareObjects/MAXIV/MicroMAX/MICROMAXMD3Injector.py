import logging
import gevent
import lucid3
import numpy as np
from PIL import Image
from mxcubecore.HardwareObjects.GenericDiffractometer import (
    GenericDiffractometer,
    DiffractometerState,
)
from mxcubecore import HardwareRepository as HWR
from mxcubecore.HardwareObjects.MAXIV.MicroMAX.MICROMAXMD3 import MICROMAXMD3

from gevent import monkey

monkey.patch_all(thread=False)

MONITORING_INTERVAL = 0.1
DEFAULT_TASK_TIMEOUT = 200
DEFAULT_TASK_RUNNING_TIMEOUT = 2
DEFAULT_PHASE_TIMEOUT = 60


class MICROMAXMD3Injector(MICROMAXMD3):

    def init(self):
        super().init()
        self.phases = {"DataCollection": 
                {
                "beamstop": "BEAM",
                "capillary": "BEAM",
                "aperture": "BEAM",
                "back_light": "OUT",
                },
                "Centring":
                {
                "beamstop": "PARK",
                "capillary": "PARK",
                "aperture": "OFF",
                "back_light": "IN",
                },
                "Transfer":
                {
                "beamstop": "PARK",
                "capillary": "PARK",
                "aperture": "OFF",
                "back_light": "OUT",
                },
                "BeamLocation":
                {
                "beamstop": "PARK",
                "capillary": "PARK",
                "aperture": "OFF",
                "back_light": "OUT",
                },
        }
        self.phase_positions = {
            "beamstop": None,
            "capillary": None,
            "aperture": None,
            "back_light": None,
        }

    def current_phase_changed(self, current_phase):
        
        if current_phase != "DataCollection":
            error_msg = "Please keep MD3 in DataCollection phase (in MD3 application) for injector mode!"
            logging.getLogger("user_level_log").error(error_msg)
        else:
            pos = self.phase_positions
            pos["beamstop"] = self.channel_dict["BeamstopPosition"].get_value()
            pos["capillary"] = self.channel_dict["CapillaryPosition"].get_value()
            pos["aperture"] = self.channel_dict["AperturePosition"].get_value()
            pos["back_light"] = self.back_light_switch.get_value().name # IN our OUT
            if pos == self.phases["DataCollection"]:
                self.current_phase = "DataCollection"
            elif pos == self.phases["Centring"]:
                self.current_phase = "Centring"
            elif pos == self.phases["Transfer"]:
                self.current_phase = "Transfer"
            elif pos == self.phases["BeamLocation"]:
                self.current_phase = "BeamLocation"
            else:
                self.current_phase = "UNKNOWN"
            logging.getLogger("HWR").info("MD3 phase changed to {}".format(current_phase))
            self.emit("phaseChanged", (current_phase,))


    def set_phase(self, phase, wait=False, timeout=None):

        try:
            if self.current_phase == "UNKNOWN":
                self.wait_device_ready(DEFAULT_PHASE_TIMEOUT) 
                self.current_phase = self.get_current_phase()
                if self.current_phase == "UNKNOWN":
                    raise Exception(
                        "Cannot determine the current MD3 phase, please set to DataCollection phase in MD3 application"
                    )
        except Exception as ex:
            error_msg = "[MICROMAXMD3] Error while changing MD3 phase from {} to {}, {}".format(
                    self.current_phase,
                    phase,
                    ex,
                )
            logging.getLogger("HWR").error(error_msg)
            raise Exception(error_msg)
        self.current_phase = phase
        logging.getLogger("HWR").info("MD3 phase changed to %s" % current_phase)
        self.emit("phaseChanged", (current_phase,))

