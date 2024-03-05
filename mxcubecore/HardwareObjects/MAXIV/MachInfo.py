"""
[Name] MachInfoMockup

[Description]
MachInfo hardware objects are used to obtain information from the accelerator
control system.

This is a mockup hardware object, it simulates the behaviour of an accelerator
information by :

    - produces a current value that varies with time
    - simulates a control room message that changes with some condition
      ()
    - simulates

[Emited signals]
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
import time
import PyTango
from mxcubecore import HardwareRepository as HWR
from mxcubecore.HardwareObjects.abstract.AbstractMachineInfo import (
    AbstractMachineInfo,
)
import re

CLEANR = re.compile("<.*?>")


def cleanhtml(raw_html):
    cleantext = re.sub(CLEANR, "", raw_html)
    return cleantext


class MachInfo(AbstractMachineInfo):
    def __init__(self, *args):
        AbstractMachineInfo.__init__(self, *args)
        self.mach_info_channel = None
        self.mach_curr_channel = None

    def init(self):
        try:
            channel = self.get_property("mach_info")
            self.mach_info_channel = PyTango.DeviceProxy(channel)
        except Exception as ex:
            logging.getLogger("HWR").warning("Error initializing machine info channel")

        try:
            channel_current = self.get_property("current")
            self.curr_info_channel = PyTango.DeviceProxy(channel_current)
        except Exception as ex:
            logging.getLogger("HWR").warning("Error initializing current info channel")
        self._run()

    def _run(self):
        gevent.spawn(self._update_me)

    def _update_me(self):
        self.t0 = time.time()
        while True:
            gevent.sleep(30)
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
                curr = self.curr_info_channel.Current
            except:
                curr = 0.00

            if curr < 0:
                self._current = 0.00
            else:
                self._current = "{:.2f}".format(curr * 1000)
            try:
                self._lifetime = float(
                    "{:.2f}".format(self.curr_info_channel.Lifetime / 3600)
                )
            except:
                self._lifetime = 0.00

            self.attention = False
            values = dict()
            values["current"] = self._current
            values["message"] = self._message
            values["lifetime"] = self._lifetime
            values["attention"] = self.attention
            self.emit("machInfoChanged", values)
            self.emit("valueChanged", values)

    def get_current(self):
        return self._current

    def get_lifeTime(self):
        return self._lifetime

    def get_topup_remaining(self):
        return self._topup_remaining

    def get_message(self):
        return self._message
