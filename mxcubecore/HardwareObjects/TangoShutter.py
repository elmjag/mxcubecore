# -*- coding: utf-8 -*-
"""
File:  TangoShutter.py

Description:
---------------------------------------------------------------
Hardware Object to provide Shutter functionality through Tango
or other compatible system. In fact any combination of HardwareRepository
commands/states will work.

Two possible situations are supported by this hardware object:
    - One state attribute
    - Two action commands (in/out, open/close, insert/extract..)

 or
    - One read/write attribute with two states

Signals
---------------------------------------------------------------
This hardware object will emit signals:

    stateChanged(new_state)

The `new_state` will be one string out of:

    'closed',
    'opened',
    'standby',
    'alarm',
    'unknown',
    'fault',
    'disabled',
    'moving',
    'init',
    'automatic',
    'running',
    'insert',
    'extract',

The state strings will be converted from the state reported by the hardware by a conversion
table detailed below. This table is inspired in the Tango.DevState possible values, but also
in other cases like for example an attribute being True/False or other known real cases.

Methods
---------------------------------------------------------------
   openShutter()
   closeShutter()

Hardware to Shutter State conversion
---------------------------------------------------------------

The following table details the conversion to shutter states from
hardware state::

  --------- --------------- ---------------
  Hardware   Shutter         PyTango.DevState
  --------- --------------- -------------------
    False    'closed'
    True     'opened'
    0        'closed'
    1        'opened'
    4        'insert'
    5        'extract'
    6        'moving'
    7        'standby'
    8        'fault'
    9        'init'
   10        'running'
   11        'alarm'
   12        'disabled'
   13        'unknown'
   -1        'fault'
   None      'unknown'
  '_'        'automatic'
  'UNKNOWN'  'unknown'        UNKNOWN
  'CLOSE'    'closed'         CLOSE
  'OPEN'     'opened'         OPEN
  'INSERT'   'closed'         INSERT
  'EXTRACT'  'opened'         EXTRACT
  'MOVING'   'moving'         MOVING
  'RUNNING'  'moving'         MOVING
  'FAULT'    'fault'          FAULT
  'DISABLE'  'disabled'       DISABLE
  'ON'       'unknown'        ON
  'OFF'      'fault'          OFF
  'STANDBY'  'standby'        STANDBY
  'ALARM'    'alarm'          ALARM
  'INIT'     'init'           INIT
  --------- ---------------

XML Configuration Example:
---------------------------------------------------------------

* With state attribute and open/close commands

<device class = "TangoShutter">
  <username>FrontEnd</username>
  <tangoname>c-x1/sh-c1-4/1</tangoname>
  <command type="tango" name="Open">Open</command>
  <command type="tango" name="Close">Close</command>
  <channel type="tango" name="State" polling="1000">State</channel>
</device>

* With read/write attribute :

In the example the tango attribute is called "exper_shutter"

<device class = "TangoShutter">
  <username>Fast Shutter</username>
  <channel type="tango" name="State" tangoname="c-x2/sh-ex-12/fs" polling="events">exper_shutter</channel>
</device>

"""
from enum import Enum, unique
from mxcubecore.HardwareObjects.abstract.AbstractShutter import AbstractShutter
from mxcubecore.BaseHardwareObjects import HardwareObjectState
import logging


@unique
class ShutterStates(Enum):
    """Shutter states definitions."""

    OPEN = HardwareObjectState.READY, 6
    CLOSE = HardwareObjectState.READY, 7
    MOVING = HardwareObjectState.BUSY, 8
    DISABLED = HardwareObjectState.WARNING, 9
    AUTOMATIC = HardwareObjectState.READY, 10

# <command type="tango" tangoname="b311a-o/pss/bs-01" name="Open">Open</command>
#   <command type="tango" tangoname="b311a-o/pss/bs-01" name="Close">Close</command>
#   <channel type="tango" name="State" tangoname="b311a-o/pss/bs-01" polling="1000">State</channel

@unique
class BaseValueEnum(Enum):
    """Defines only the compulsory values."""

    OPEN = "OPEN"
    CLOSE = "CLOSE"
    UNKNOWN = "UNKNOWN"

class TangoShutter(AbstractShutter):
    VALUES = BaseValueEnum

    def init(self):
        self.state_value_str = "unknown"
        try:
            self.shutter_channel = self.get_channel_object("State")
            self.shutter_channel.connect_signal("update", self.shutter_state_changed)
        except KeyError:
            logging.getLogger().warning(
                "%s: cannot connect to shutter channel", self.name()
            )

        self.open_cmd = self.get_command_object("Open")
        self.close_cmd = self.get_command_object("Close")

    def shutter_state_changed(self, value):
        self.state_value_str = self._convert_state_to_str(value)
        self.emit("shutterStateChanged", (self.state_value_str,))

    def _convert_state_to_str(self, value):
        state = str(value).upper()
        try:
            state_str = ShutterStates[state]
        except KeyError:
            state_str = "unknown"
        return state_str

    # def readShutterState(self):
    #     state = self.shutter_channel.get_value(   )
    #     return self._convert_state_to_str(state)

    def getShutterState(self):
        return self.state_value_str

    def get_value(self):
        state = self.shutter_channel.get_value()
        try:
            value = self.VALUES[str(state)]
        except KeyError:
            value = "UNKNOWN"
        return value

    def _set_value(self, value):
        """Implementation of specific set actuator logic.
        Args:
            value: target value
        """
        print('_set_value', value)
        if value.value == 'OPEN':
            self.open()
        elif value.value == 'CLOSE':
            self.close()  

    def open(self, timeout=None):
        # Try getting open command configured in xml
        # If command is not defined then try writing the channel
        if self.open_cmd is not None:
            self.open_cmd()
        else:
            self.shutter_channel.set_value(True)

    def close(self):
        # Try getting close command configured in xml
        # If command is not defined try writing the channel
        if self.close_cmd is not None:
            self.close_cmd()
        else:
            self.shutter_channel.set_value(False)
