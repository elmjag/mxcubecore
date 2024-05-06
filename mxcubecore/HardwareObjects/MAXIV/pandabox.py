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

    # avoid reloading schema if it is already loaded,
    # this way we don't reset attributes to default values,
    # allowing users to tweak parameters outside MXCuBE
    if dev.Schema != "ssx_inject":
        dev.Schema = "ssx_inject"

    dev.EnableEiger = conf.enable_eiger
    dev.EnableCustomOutput = conf.enable_custom_output
    dev.CustomOutputDelay = conf.custom_output_delay
    dev.CustomOutputPulseWidth = conf.custom_output_pulse_width

    # make sure measurement not running, before resetting counters,
    # otherwise counters will have bogus values
    dev.EnableMeasurement = False

    #
    # reset counters
    #
    dev.EnableShutterCount = False
    dev.EnableShutterCount = True

    dev.EnableJungfrauCount = False
    dev.EnableJungfrauCount = True


def _set_enable_measurement(enabled: bool):
    _get_tango_dev().EnableMeasurement = enabled


def start_measurement():
    _set_enable_measurement(True)


def stop_measurement():
    _set_enable_measurement(False)
