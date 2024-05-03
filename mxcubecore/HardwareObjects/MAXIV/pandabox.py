import logging
from tango import DeviceProxy
from dataclasses import dataclass


TANGO_DEVICE = "B312A-A101232-CAB01/CTL/PANDA-01"


log = logging.getLogger("HWR")


@dataclass
class SSXInjectConfig:
    enable_eiger: bool = False
    enable_jungfrau: bool = False
    enable_custom_output: bool = False
    custom_output_delay: float = 0.0
    custom_output_pulse_width: float = 0.0


def _get_tango_dev():
    return DeviceProxy(TANGO_DEVICE)


def load_ssx_inject_schema(conf: SSXInjectConfig):
    log.info(f"[PandABox] configuring 'ssx_inject' schema with {conf}")

    dev = _get_tango_dev()
    dev.Schema = "ssx_inject"
    dev.EnableEiger = conf.enable_eiger
    dev.EnableJungfrau = conf.enable_jungfrau
    dev.EnableCustomOutput = conf.enable_custom_output
    dev.CustomOutputDelay = conf.custom_output_delay
    dev.CustomOutputPulseWidth = conf.custom_output_pulse_width


def _set_clock_running(clock_running: bool):
    # here we assume that 'ssx_inject' schema is loaded
    log.info(f"[PandABox] setting ClockRunning to {clock_running}")
    _get_tango_dev().ClockRunning = clock_running


def start_clock():
    _set_clock_running(True)


def stop_clock():
    _set_clock_running(False)
