import logging

from mxcubecore import HardwareRepository as HWR

log = logging.getLogger("HWR")


class PrepareOpenHutch:
    """
    Prepare beamline for opening the hutch door.

    - close safety shutter
    - close detector cover
    - move detector to a safe position
    - put MD3 into 'Transfer' phase
    - if jungfrau is used, take pedestal
    """

    def __call__(self, *args, **kw):
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
            log.exception(f"Error preparing to open hutch.\nError was: '{str(ex)}'")


class MeasureFlux:
    def __call__(self, *args, **kw):
        """
        calculate flux at sample position
        """
        flux_at_sample = HWR.beamline.collect.get_instant_flux()
        log.info(f"Flux at sample position is {flux_at_sample:.2e} ph/s")
