import logging

from tango import DeviceProxy

from mxcubecore import HardwareRepository as HWR  # noqa: N814
from mxcubecore.HardwareObjects.MAXIV.MAXIVMD3 import NoPositionBookmarkedError
from mxcubecore.utils.units import kev_to_ev

log = logging.getLogger("user_level_log")


class PrepareOpenHutch:
    """
    Prepare beamline for opening the hutch door.

    - close safety shutter
    - close detector cover
    - move detector to a safe position
    - put MD3 into 'Transfer' phase
    - if jungfrau is used, take pedestal
    """

    def __call__(self):
        try:
            collect = HWR.beamline.collect
            diffractometer = HWR.beamline.diffractometer
            detector = HWR.beamline.detector

            log.info("Preparing experimental hutch for door opening.")

            collect.close_safety_shutter()
            collect.close_detector_cover()

            log.info("Setting diffractometer to transfer phase.")
            diffractometer.wait_device_ready()
            diffractometer.set_phase("Transfer")

            log.info("Moving detector to safe position.")
            collect.move_detector_to_safe_position()

            if detector.get_property("model") == "JUNGFRAU":
                log.info("Collecting Jungfrau pedestal.")
                detector.pedestal()

        except Exception as ex:
            # Explicitly add raised exception into the log message,
            # so that it is shown to the user in the beamline action UI log.
            log.exception("Error preparing to open hutch.\nError was: '%s'", str(ex))  # noqa: TRY401


class CheckBeam:
    def __call__(self):
        """
        Check beam stability
        """
        xbpms = {
            "DM3": DeviceProxy("b312a-o06/dia/xbpm-01"),
            "DM4": DeviceProxy("b312a-e01/dia/xbpm-01"),
            "BCU XBPM1": DeviceProxy("b312a-e04/dia/xbpm-01"),
            "BCU XBPM2": DeviceProxy("b312a-e04/dia/xbpm-02"),
        }
        energy = kev_to_ev(HWR.beamline.energy.get_value())
        transmission = HWR.beamline.transmission.get_value()
        for name, xbpm in xbpms.items():
            total_current = xbpm.S
            flux = total_current * (
                -0.534515 * energy**4
                - 43197.6 * energy**3
                + 5.13449e09 * energy**2
                - 4.39169e13 * energy
                + 1.14591e17
            )
            log.info(
                f"XBPM: {name}, total current: {total_current * 1e6:.2f} uA, "
                f"estimated flux at sample position: {flux:.2e} ph/s"
            )

            if "BCU" in name:
                full_flux = flux * 100.0 / transmission
                log.info(
                    f"Current transmission: {transmission:.2f}%, "
                    f"estimated full flux at sample position: {full_flux:.2e} ph/s"
                )


class MeasureFlux:
    def __call__(self):
        """
        calculate flux at sample position
        """
        flux_at_sample = HWR.beamline.collect.get_instant_flux()
        log.info("Flux at sample position is %.2e ph/s", flux_at_sample)


class SaveMD3Position:
    def __call__(self):
        HWR.beamline.diffractometer.bookmark_position()


class MoveToMD3SavedPosition:
    def __call__(self):
        try:
            HWR.beamline.diffractometer.goto_bookmarked_position()
        except NoPositionBookmarkedError:
            log.warning("No MD3 position saved.")
