import os
import logging
import contextlib
import enum
import subprocess

from pydantic import BaseModel, Field
from devtools import debug

from mxcubecore.model.common import (
    CommonCollectionParamters,
    PathParameters,
    LegacyParameters,
    StandardCollectionParameters,
)

from mxcubecore import HardwareRepository as HWR

from mxcubecore.HardwareObjects.ESRF.queue_entry.ssx_base_queue_entry import (
    SsxBaseQueueEntry,
)

from mxcubecore.model.queue_model_objects import (
    DataCollection,
)


__credits__ = ["MXCuBE collaboration"]
__license__ = "LGPLv3+"
__category__ = "General"


class SSXUserCollectionParameters(BaseModel):
    sub_sampling: float = Field(4, gt=0, lt=100)
    exp_time: float = Field(100e-6, gt=0, lt=1)
    motor_top_left_x: float = Field(18, gt=-100, lt=100)
    motor_top_left_y: float = Field(15.8, gt=-100, lt=100)
    motor_top_left_z: float = Field(-0.17, gt=-100, lt=100)

    motor_top_right_x: float = Field(22, gt=-100, lt=100)
    motor_top_right_y: float = Field(15.8, gt=-100, lt=100)
    motor_top_right_z: float = Field(-0.17, gt=-100, lt=100)

    motor_bottom_left_x: float = Field(18, gt=-100, lt=100)
    motor_bottom_left_y: float = Field(24, gt=-100, lt=100)
    motor_bottom_left_z: float = Field(-0.17, gt=-100, lt=100)

    nb_samples_per_line: int = Field(100, gt=0, lt=1000)
    nb_lines: int = Field(800, gt=0, lt=1000)
    take_pedestal: bool = Field(True)

    class Config:
        extra: "ignore"


class SsxFoilColletionTaskParameters(BaseModel):
    path_parameters: PathParameters
    common_parameters: CommonCollectionParamters
    collection_parameters: StandardCollectionParameters
    user_collection_parameters: SSXUserCollectionParameters
    legacy_parameters: LegacyParameters


class SsxFoilCollectionQueueModel(DataCollection):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class SsxFoilCollectionLima2QueueEntry(SsxBaseQueueEntry):
    """
    Defines the behaviour of a data collection.
    """

    QMO = SsxFoilCollectionQueueModel
    DATA_MODEL = SsxFoilColletionTaskParameters
    NAME = "SSX Foil Collection (Lima2)"
    REQUIRES = ["point", "line", "no_shape", "chip", "mesh"]

    def __init__(self, view, data_model: SsxFoilCollectionQueueModel):
        super().__init__(view=view, data_model=data_model)

    def execute(self):
        super().execute()
        debug(self._data_model._task_data)
        params = self._data_model._task_data.user_collection_parameters

        MAX_FREQ = 925.0
        packet_fifo_depth = 20000

        exp_time = self._data_model._task_data.user_collection_parameters.exp_time
        num_images = params.nb_samples_per_line * params.nb_lines
        self._data_model._task_data.collection_parameters.num_images = num_images
        fname_prefix = self._data_model._task_data.path_parameters.prefix
        data_root_path, _ = self.get_data_path()

        self.take_pedestal_lima2(MAX_FREQ)

        logging.getLogger("user_level_log").info("Preparing detector")
        HWR.beamline.detector.prepare_acquisition(
            num_images, exp_time, data_root_path, fname_prefix
        )

        HWR.beamline.detector.wait_ready()

        fname_prefix = self._data_model._task_data.path_parameters.prefix
        fname_prefix += f"_foil_"

        region = (
            params.motor_top_left_x,
            params.motor_top_left_y,
            params.motor_top_left_z,
            params.motor_top_right_x,
            params.motor_top_right_y,
            params.motor_top_right_z,
            params.motor_bottom_left_x,
            params.motor_bottom_left_y,
            params.motor_bottom_left_z,
        )

        self.start_processing("FOIL")

        logging.getLogger("user_level_log").info(f"Defining region {region}")

        HWR.beamline.diffractometer.define_ssx_scan_region(
            *region, params.nb_samples_per_line, params.nb_lines
        )

        HWR.beamline.diffractometer.wait_ready()
        HWR.beamline.diffractometer.set_phase("DataCollection", wait=True, timeout=120)

        if HWR.beamline.control.safshut_oh2.state.name != "OPEN":
            logging.getLogger("user_level_log").info(f"Opening OH2 safety shutter")
            HWR.beamline.control.safshut_oh2.open()

        HWR.beamline.detector.start_acquisition()
        logging.getLogger("user_level_log").info(
            "Detector ready, waiting for trigger ..."
        )

        logging.getLogger("user_level_log").info(f"Acquiring {num_images}")

        try:
            HWR.beamline.diffractometer.start_ssx_scan(params.sub_sampling)
            HWR.beamline.diffractometer.wait_ready()
        except:
            msg = "Diffractometer failed! Waiting for detector to finish"
            logging.getLogger("user_level_log").error(msg)
            HWR.beamline.detector.wait_ready()
            raise

        if HWR.beamline.control.safshut_oh2.state.name == "OPEN":
            HWR.beamline.control.safshut_oh2.close()
            logging.getLogger("user_level_log").info("shutter closed")

        HWR.beamline.detector.wait_ready()
        logging.getLogger("user_level_log").info(f"Acquired {region}")

    def pre_execute(self):
        super().pre_execute()

    def post_execute(self):
        super().post_execute()

    def stop(self):
        super().stop()
