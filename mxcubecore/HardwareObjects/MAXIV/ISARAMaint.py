from tango import DeviceProxy
from mxcubecore.BaseHardwareObjects import Equipment


class ISARAMaint(Equipment):
    def __init__(self, name):
        super().__init__(name)

        self._commands_state = dict(
            powerOn=False,
            powerOff=False,
            openLid=True,
            closeLid=True,
            home=True,
            dry=True,
            soak=True,
            clearMemory=True,
            reset=True,
            back=True,
            abort=True,
        )

        self._powered = None
        self._position_name = None
        self._message = None

    def init(self):
        self.isara_dev = DeviceProxy(self.tangoname)

        self._poll_attribute("Powered", self._powered_updated)
        self._poll_attribute("PositionName", self._position_name_updated)
        self._poll_attribute("Message", self._message_updated)

    def _poll_attribute(self, attr_name: str, callback):
        channel = self.add_channel(
            {
                "type": "tango",
                "name": f"_chn{attr_name}",
                "tangoname": self.tangoname,
                "polling": 1000,
            },
            attr_name,
        )

        channel.connect_signal("update", callback)

    def _update_command_states(self):
        if self._powered is None or self._position_name is None:
            # some of the values are still unknown,
            # wait until we get all values
            return

        #
        # update 'power' commands
        #
        self._commands_state["powerOn"] = not self._powered
        self._commands_state["powerOff"] = self._powered

        #
        # update 'positions' commands
        #
        if not self._powered or self._position_name == "undefined":
            # when powered off or running a trajectory,
            # disable position commands
            self._commands_state["home"] = False
            self._commands_state["dry"] = False
            self._commands_state["soak"] = False
        else:
            self._commands_state["home"] = True
            self._commands_state["dry"] = True
            self._commands_state["soak"] = True

            if self._position_name in ["home", "dry", "soak"]:
                # can't move to same position
                self._commands_state[self._position_name] = False

        self._emit_global_state_changed()

    def _powered_updated(self, powered):
        self._powered = powered
        self._update_command_states()

    def _position_name_updated(self, position_name):
        self._position_name = position_name.lower()
        self._update_command_states()

    def _message_updated(self, message):
        self._message = message
        self._emit_global_state_changed()

    def _emit_global_state_changed(self):
        self.emit(
            "globalStateChanged",
            (self._commands_state, self._message),
        )

    def send_command(self, cmd_name, _args=None):
        if cmd_name == "powerOn":
            self.isara_dev.PowerOn()
        elif cmd_name == "powerOff":
            self.isara_dev.PowerOff()
        elif cmd_name == "openLid":
            self.isara_dev.OpenLid()
        elif cmd_name == "closeLid":
            self.isara_dev.CloseLid()
        elif cmd_name == "home":
            self.isara_dev.Home()
        elif cmd_name == "dry":
            self.isara_dev.Dry()
        elif cmd_name == "soak":
            self.isara_dev.Soak()
        elif cmd_name == "clearMemory":
            self.isara_dev.ClearMemory()
        elif cmd_name == "reset":
            self.isara_dev.Reset()
        elif cmd_name == "back":
            self.isara_dev.Back()
        elif cmd_name == "abort":
            self.isara_dev.Abort()
        else:
            raise Exception(f"ISARA MAINT: unexpected command '{cmd_name}'")

    def get_global_state(self):
        return dict(glob_state="dummy"), self._commands_state, self._message

    def get_cmd_info(self):
        return [
            [
                "Power",
                [
                    ["powerOn", "PowerOn", "Switch Power On"],
                    ["powerOff", "PowerOff", "Switch Power Off"],
                ],
            ],
            [
                "Lid",
                [
                    ["openLid", "Open Lid", "Open Lid"],
                    ["closeLid", "Close Lid", "Close Lid"],
                ],
            ],
            [
                "Positions",
                [
                    ["home", "Home", "Actions", "Home (trajectory)"],
                    ["dry", "Dry", "Actions", "Dry (trajectory)"],
                    ["soak", "Soak", "Actions", "Soak (trajectory)"],
                ],
            ],
            [
                "Recovery",
                [
                    [
                        "clearMemory",
                        "Clear Memory",
                        "Clear Info in Robot Memory "
                        " (includes info about sample on Diffr)",
                    ],
                    [
                        "reset",
                        "Reset Fault",
                        "Acknowledge security fault",
                    ],
                    [
                        "back",
                        "Back",
                        "Return sample back to Dewar",
                    ],
                ],
            ],
            ["Abort", [["abort", "Abort", "Abort running trajectory"]]],
        ]
