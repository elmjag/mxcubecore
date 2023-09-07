from mxcubecore.BaseHardwareObjects import HardwareObject
from mxcubecore.HardwareObjects.abstract.sample_changer.Container import Container
from mxcubecore.HardwareObjects.abstract.sample_changer.Sample import Sample


NUM_PUCKS = 29  # number of pucks in the dewar


def _get_pin_address(puck: "_Unipuck", pin_no: int):
    return f"{puck.get_address()}:{pin_no:02}"


class Pin(Sample):
    STD_HOLDERLENGTH = 22.0

    def __init__(self, puck: "_Unipuck", pin_no: int):
        super().__init__(puck, _get_pin_address(puck, pin_no), False)
        self._set_holder_length(Pin.STD_HOLDERLENGTH)
        self._set_info(False, None, False)

    def get_basket_no(self):
        return self.get_container().get_index() + 1


class _Unipuck(Container):
    NUM_PINS = 16

    def __init__(self, sample_changer, position: int):
        Container.__init__(self, "Puck", sample_changer, str(position), False)

        self._set_info(False, "", False)

        for pos in range(1, self.NUM_PINS + 1):
            pin = Pin(self, pos)
            self._add_component(pin)

    def set_present(self, present: bool):
        self._set_info(present, "", False)

        pin_id = "          " if present else None

        for pin in self.components:
            pin._set_info(present, pin_id, False)


class Meep(Container, HardwareObject):
    # def _dbg(self):
    #     print("************** PUCKS ******************")
    #     for puck in self.components:
    #         print(f"puck {puck=}")
    #         for pin in puck.components:
    #             print(f"    pin {pin=} {pin.get_address()=}")
    #
    #     print("***************************************")

    def __init__(self, name):
        Container.__init__(self, "ISARA", None, "Sample Changer", False)
        HardwareObject.__init__(self, name)

        for pos in range(1, NUM_PUCKS + 1):
            puck = _Unipuck(self, pos)
            self._add_component(puck)

        for n in [0, 2, 11, 15]:
            puck = self.components[n]
            puck.set_present(True)

    def get_loaded_sample(self):
        return None
