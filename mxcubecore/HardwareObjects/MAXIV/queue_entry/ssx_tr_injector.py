import json
import gevent
import logging
from pydantic import BaseModel, Field
from mxcubecore import HardwareRepository as HWR
from mxcubecore.model.queue_model_objects import DataCollection
from mxcubecore.model.common import (
    CommonCollectionParamters,
    PathParameters,
    LegacyParameters,
    StandardCollectionParameters,
)
from mxcubecore.HardwareObjects.MAXIV import pandabox
from .base import AbstractSsxQueueEntry


log = logging.getLogger("queue_exec")


def sec_to_ms(sec) -> float:
    """
    convert seconds to milliseconds (ms)
    """
    return sec * 1_000.0


class InjectorUserCollectionParameters(BaseModel):
    exp_time: float = Field(100e-6, gt=0, lt=1, title="Exposure time (s)")
    num_images: int = Field(1000, gt=0, lt=10000000, title="Number of images")
    num_triggers: int = Field(1000, gt=0, lt=300_000, title="Number of triggers")
    energy: float = Field()
    resolution: float = Field()
    laser_pulse_delay: float = Field(0, title="Laser pulse delay (s)")
    laser_pulse_width: float = Field(0, title="Laser pulse width (s)")


class SsxTrInjectorQueueModel(DataCollection):
    pass


class InjectorTaskParameters(BaseModel):
    path_parameters: PathParameters
    common_parameters: CommonCollectionParamters
    collection_parameters: StandardCollectionParameters
    user_collection_parameters: InjectorUserCollectionParameters
    legacy_parameters: LegacyParameters

    @staticmethod
    def update_dependent_fields(field_data):
        #
        # Jungfrau specific hacks
        #
        storage_cell_count = HWR.beamline.detector.get_storage_cell_count()
        field_data["num_images"] = storage_cell_count * field_data["num_triggers"]

        return field_data

    @staticmethod
    def ui_schema():
        return json.dumps(
            {
                "ui:order": [
                    "num_triggers",
                    "num_images",
                    "exp_time",
                    "resolution",
                    "energy",
                    "*",
                ],
                "ui:submitButtonOptions": {
                    "norender": "true",
                },
                "num_images": {"ui:readonly": "true"},
            }
        )


class SsxTrInjectorQueueEntry(AbstractSsxQueueEntry):
    QMO = SsxTrInjectorQueueModel
    DATA_MODEL = InjectorTaskParameters
    NAME = "SSX Injector Time Resolved"
    REQUIRES = ["point", "line", "no_shape", "chip", "mesh"]

    def execute(self):
        super().execute()

        num_triggers = (
            self._data_model._task_data.user_collection_parameters.num_triggers
        )
        self.prepare_data_collection(num_triggers)

        #
        # configure pandABox to generate desired trigger signals
        #
        params = self._data_model._task_data.user_collection_parameters
        ssx_cfg = pandabox.SSXInjectConfig(
            enable_jungfrau=True,
            enable_custom_output=True,
            custom_output_delay=sec_to_ms(params.laser_pulse_delay),
            custom_output_pulse_width=sec_to_ms(params.laser_pulse_width),
        )
        pandabox.load_ssx_inject_schema(ssx_cfg)

        #
        # start acquisition
        #
        pandabox.start_measurement()

        #
        # wait for acquisition to end
        #
        log.info("Waiting for acquisition to finish.")
        HWR.beamline.detector.wait_ready()
        log.info("Acquisition is finished.")

        #
        # stop generating trigger signals
        #
        pandabox.stop_measurement()

    def stop(self):
        # stop generating trigger signals
        pandabox.stop_measurement()
        # give detector chance to finish last train of triggers
        gevent.sleep(1.0)

        # this will ask detector to stop acquisition
        super().stop()
