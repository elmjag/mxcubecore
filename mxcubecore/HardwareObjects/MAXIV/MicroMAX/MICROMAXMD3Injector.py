import logging
import time
from mxcubecore.HardwareObjects.MAXIV.MicroMAX.MICROMAXMD3 import MICROMAXMD3
from gevent import monkey

monkey.patch_all(thread=False)

MONITORING_INTERVAL = 0.1
DEFAULT_TASK_TIMEOUT = 200
DEFAULT_TASK_RUNNING_TIMEOUT = 2
DEFAULT_PHASE_TIMEOUT = 60


log = logging.getLogger("HWR")


class MICROMAXMD3Injector(MICROMAXMD3):
    def __init__(self, *args):
        super().__init__(*args)
        self.phase_pos_dict = {}
        self.phases = {}

    def init(self):
        super().init()
        self.phases = {
            "DataCollection": {
                "beamstop": "BEAM",
                "capillary": "BEAM",
                "aperture": "BEAM",
                "back_light": "OUT",
                "cameraExposure": 40000,
            },
            "Centring": {
                "beamstop": "PARK",
                "capillary": "PARK",
                "aperture": "OFF",
                "back_light": "IN",
                "cameraExposure": 20000,
            },
            "Transfer": {
                "beamstop": "PARK",
                "capillary": "PARK",
                "aperture": "OFF",
                "back_light": "OUT",
                "cameraExposure": 40000,
            },
            "BeamLocation": {
                "beamstop": "PARK",
                "capillary": "OFF",
                "aperture": "OFF",
                "back_light": "OUT",
                "cameraExposure": 1000,
            },
        }
        self.phase_pos_dict = {
            "beamstop": None,
            "capillary": None,
            "aperture": None,
            "back_light": None,
            "cameraExposure": None,
        }
        self.update_current_phase()

    def current_phase_changed(self, current_phase):

        if current_phase != "DataCollection":
            error_msg = "Please keep MD3 in DataCollection phase (in MD3 application) for injector mode!"
            logging.getLogger("user_level_log").error(error_msg)
        else:
            self.update_current_phase()

    def get_current_phase_positions(self):
        pos = self.phase_pos_dict
        pos["beamstop"] = self.command_dict["getBeamstopPosition"]()
        pos["capillary"] = self.channel_dict["CapillaryPosition"].get_value()
        pos["aperture"] = self.channel_dict["AperturePosition"].get_value()
        pos["back_light"] = self.back_light_switch.get_value().name  # IN our OUT
        pos["cameraExposure"] = self.channel_dict["CameraExposure"].get_value()
        return pos

    def switch_back_light(self, value):
        back_light = self.back_light_switch
        if value == "IN":
            back_light.set_value(back_light.VALUES.IN)
        elif value == "OUT":
            back_light.set_value(back_light.VALUES.OUT)
        self.wait_device_ready(DEFAULT_PHASE_TIMEOUT)

    def switch_front_light(self, value):
        front_light = self.front_light_switch
        if value == "IN":
            front_light.set_value(front_light.VALUES.IN)
        elif value == "OUT":
            front_light.set_value(front_light.VALUES.OUT)
        self.wait_device_ready(DEFAULT_PHASE_TIMEOUT)

    def update_current_phase(self):
        pos = self.get_current_phase_positions()
        if pos == self.phases["DataCollection"]:
            current_phase = "DataCollection"
        elif pos == self.phases["Centring"]:
            current_phase = "Centring"
        elif pos == self.phases["Transfer"]:
            current_phase = "Transfer"
        elif pos == self.phases["BeamLocation"]:
            current_phase = "BeamLocation"
        else:
            current_phase = "UNKNOWN"
        if current_phase != self.current_phase:
            logging.getLogger("HWR").info(
                "MD3 phase changed to {} from {}".format(
                    current_phase, self.current_phase
                )
            )
            self.current_phase = current_phase
            self.emit("phaseChanged", (self.current_phase,))

    def set_organ_pos(self, motor_name, pos_name):
        try:
            if motor_name == "beamstop":
                self.command_dict["setBeamstopPosition"](pos_name)
                self.wait_device_ready(DEFAULT_PHASE_TIMEOUT)
                return
            elif motor_name == "cameraExposure":
                name = "CameraExposure"
            else:
                name = "{}{}Position".format(motor_name[0].upper(), motor_name[1:])
            self.channel_dict[name].set_value(pos_name)
            self.wait_device_ready(DEFAULT_PHASE_TIMEOUT)
        except Exception as ex:
            error_msg = "[MICROMAXMD3] Error while moving {} to {}, {}".format(
                motor_name, pos_name, ex
            )
            raise Exception("")
            logging.getLogger("HWR").error(error_msg)

    def set_phase(self, phase, wait=False, timeout=None):
        try:
            if self.current_phase == "UNKNOWN":
                self.wait_device_ready(DEFAULT_PHASE_TIMEOUT)
                self.current_phase = self.get_current_phase()
            # now MD3 should be in ready state and we can safely change the phase
            self.close_fast_shutter()
            time.sleep(1)
            current_phase_pos = self.get_current_phase_positions()
            if self.current_phase == "UNKNOWN":
                logging.getLogger("HWR").warning(
                    "Cannot determine the current MD3 phase, please set to DataCollection phase in MD3 application"
                )
                self.set_organ_pos("scintillatorVertical", -90)
                self.set_organ_pos("beamstop", "PARK")
                self.switch_back_light("OUT")
                self.set_organ_pos("capillary", "PARK")

            new_phase_pos = self.phases[phase]

            if self.current_phase == "BeamLocation":
                # move scintillator
                self.set_organ_pos("scintillatorVertical", -90)
                self.focus_motor_hwobj.set_value(0)
                self.wait_device_ready(DEFAULT_PHASE_TIMEOUT)
                self.set_organ_pos("AlignmentTable", "STORED")

            if new_phase_pos["beamstop"] != current_phase_pos["beamstop"]:
                if phase != "DataCollection":
                    motor_pos = new_phase_pos["beamstop"]
                    self.set_organ_pos("beamstop", motor_pos)

            organ_list = ["aperture", "capillary", "cameraExposure"]
            for organ in organ_list:
                if new_phase_pos[organ] != current_phase_pos[organ]:
                    motor_pos = new_phase_pos[organ]
                    self.set_organ_pos(organ, motor_pos)

            if new_phase_pos["back_light"] != current_phase_pos["back_light"]:
                motor_pos = new_phase_pos["back_light"]
                self.switch_back_light(motor_pos)

            # move in beamstop in the end
            if phase == "DataCollection":
                motor_pos = new_phase_pos["beamstop"]
                self.set_organ_pos("beamstop", motor_pos)
                self.switch_front_light("IN")

            if phase == "BeamLocation":
                self.phiz_motor_hwobj.set_value(5)
                self.wait_device_ready(DEFAULT_PHASE_TIMEOUT)
                # move scintillator
                self.focus_motor_hwobj.set_value(2)
                self.wait_device_ready(DEFAULT_PHASE_TIMEOUT)
                self.set_organ_pos("scintillatorVertical", 0.48)
                # one cannot move it via exporter :(
                # self.set_organ_pos("beamstopDistance", 6.863)
                self.switch_front_light("OUT")

        except Exception:
            error_msg = (
                "[MICROMAXMD3] Error while changing MD3 phase from {} to {}".format(
                    self.current_phase,
                    phase,
                )
            )
            logging.getLogger("HWR").exception(error_msg)
            raise Exception(error_msg)
        self.current_phase = phase
        logging.getLogger("HWR").info("MD3 phase changed to %s" % phase)
        self.emit("phaseChanged", (phase,))

    def abort(self):
        """
        Ignore abort request in this implementation. This method does nothing.
        """
        log.warning("[MAXIVMD3]: bypass md3 abort")

    def finish_calculate_flux(self, ori_motors, ori_phase="DataCollection"):
        self.set_phase(ori_phase, wait=True, timeout=200)
        self.wait_ready(10)
        if ori_phase == "DataCollection":
            self.channel_dict["BeamstopPosition"].set_value("BEAM")
        self.wait_ready(10)
        ori_motors.pop("phi")
        if ori_motors is not None:
            self.move_motors(ori_motors)
            self.wait_ready(10)
