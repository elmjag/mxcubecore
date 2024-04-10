"""
[Name] MachInfo

[Description]
Polls the configured accelerator status tango devices.
Reads info such as ring current, life-time, operator message, etc.

[Emitted signals]
machInfoChanged
   pars:  values (dict)

   mandatory fields:
     values['current']  type: str; desc: synchrotron radiation current in milli-amps
     values['message']  type: str; desc: message from control room
     values['attention'] type: boolean; desc: False (if no special attention is required)
                                            True (if attention should be raised to the user)

   optional fields:
      any number of optional fields can be sent over with this signal by adding them in the
      values dictionary

      for example:
         values['lifetime']
         values['topup_remaining']
"""

import logging
import gevent
import tango
from mxcubecore.HardwareObjects.abstract.AbstractMachineInfo import (
    AbstractMachineInfo,
)
import re

CLEANR = re.compile("<.*?>")


log = logging.getLogger("HWR")


def cleanhtml(raw_html):
    cleantext = re.sub(CLEANR, "", raw_html)
    return cleantext


class MachInfo(AbstractMachineInfo):
    def __init__(self, *args):
        AbstractMachineInfo.__init__(self, *args)
        self.mach_info_channel = None
        self.mach_curr_channel = None
        self._fill_mode = None

    def init(self):
        self._fill_mode = self.get_property("filling_mode")

        try:
            channel = self.get_property("mach_info")
            self.mach_info_channel = tango.DeviceProxy(channel)
        except Exception:
            log.warning("Error initializing machine info channel", exc_info=True)

        try:
            channel_current = self.get_property("current")
            self.mach_curr_channel = tango.DeviceProxy(channel_current)
        except Exception:
            log.warning("Error initializing current info channel", exc_info=True)

        gevent.spawn(self._poll_info)

    def _poll_info(self):
        while True:
            _machine_message = cleanhtml(self.mach_info_channel.MachineMessage)
            _machine_message = _machine_message.replace("R1", "\nR1")
            _machine_message = _machine_message.replace("Linac", "\nLinac")
            self._message = _machine_message
            self._message += "\nOperator mesage: " + cleanhtml(
                self.mach_info_channel.OperatorMessage
            )
            self._message += (
                "\nNext injection: " + self.mach_info_channel.R3NextInjection
            )
            self._topup_remaining = self.mach_info_channel.R3TopUp
            try:
                curr = self.mach_curr_channel.Current
            except:
                curr = 0.00

            if curr < 0:
                self._current = 0.00
            else:
                self._current = "{:.2f}".format(curr * 1000)
            try:
                self._lifetime = float(
                    "{:.2f}".format(self.mach_curr_channel.Lifetime / 3600)
                )
            except:
                self._lifetime = 0.00

            self.attention = False
            values = dict()
            values["current"] = self._current
            values["message"] = self._message
            values["lifetime"] = self._lifetime
            values["attention"] = self.attention
            self.emit("valueChanged", values)

            gevent.sleep(30)

    def get_current(self):
        return self._current

    def get_lifetime(self):
        return self._lifetime

    def get_topup_remaining(self):
        return self._topup_remaining

    def get_fill_mode(self) -> str:
        return self._fill_mode

    def get_message(self):
        return self._message
