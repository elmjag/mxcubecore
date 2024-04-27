import json
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from mxcubecore.queue_entry.base_queue_entry import BaseQueueEntry
from mxcubecore.model.queue_model_objects import DataCollection
from mxcubecore import HardwareRepository as HWR
from mxcubecore.model.common import (
    CommonCollectionParamters,
    PathParameters,
    LegacyParameters,
    StandardCollectionParameters,
)

log = logging.getLogger("queue_exec")


class InjectorUserCollectionParameters(BaseModel):
    exp_time: float = Field(100e-6, gt=0, lt=1, title="Exposure time (s)")
    num_images: int = Field(1000, gt=0, lt=10000000, title="Number of images")
    energy: float
    resolution: float


class SsxInjectorQueueModel(DataCollection):
    pass


class InjectorTaskParameters(BaseModel):
    path_parameters: PathParameters
    common_parameters: CommonCollectionParamters
    collection_parameters: StandardCollectionParameters
    user_collection_parameters: InjectorUserCollectionParameters
    legacy_parameters: LegacyParameters

    @staticmethod
    def update_dependent_fields(field_data):
        return field_data

    @staticmethod
    def ui_schema():
        return json.dumps(
            {
                "ui:order": [
                    "num_images",
                    "exp_time",
                    "resolution",
                    "energy",
                    "*",
                ],
                "ui:submitButtonOptions": {
                    "norender": "true",
                },
                "sub_sampling": {"ui:readonly": "true"},
                "frequency": {"ui:readonly": "true"},
            }
        )


class SsxInjectorQueueEntry(BaseQueueEntry):
    QMO = SsxInjectorQueueModel
    DATA_MODEL = InjectorTaskParameters
    NAME = "SSX Injector Collection"
    REQUIRES = ["point", "line", "no_shape", "chip", "mesh"]

    def pre_execute(self):
        super().pre_execute()

        #
        # this is probably wrong approach, but let's use it for now
        #
        # make sure the 'run number' of the task is increased each time
        # we launch a new data collection run
        #
        path_template = self._data_model.acquisitions[0].path_template
        queue_model = HWR.beamline.queue_model
        path_template.run_number = queue_model.get_next_run_number(path_template)

    def execute(self):
        def get_params():
            td = self._data_model._task_data
            dc_dict = self._data_model.as_dict()
            uc_params = td.user_collection_parameters
            col_params = td.collection_parameters

            return (
                uc_params.exp_time,
                uc_params.num_images,
                col_params.energy,
                col_params.resolution,
                dc_dict["path"],
                td.path_parameters.prefix,
                dc_dict["run_number"],
            )

        def get_hwobjs():
            beamline = HWR.beamline
            return beamline.detector, beamline.collect, beamline.diffractometer

        super().execute()

        #
        # fetch task parameters from model object
        #
        (
            exp_time,
            num_images,
            energy,
            resolution,
            root_dir,
            path_prefix,
            run_number,
        ) = get_params()

        detector, collect, diffractometer = get_hwobjs()

        #
        # move detector for selected resolution
        #
        collect.set_resolution(resolution)

        #
        # configure and arm detector
        #
        beam_center_x, beam_center_y = collect.get_beam_centre()
        det_cfg = detector.col_config
        det_cfg["NbImages"] = num_images
        det_cfg["OmegaStart"] = 0.0
        det_cfg["OmegaIncrement"] = 0.0
        det_cfg["BeamCenterX"] = beam_center_x
        det_cfg["BeamCenterY"] = beam_center_y
        det_cfg["DetectorDistance"] = collect.get_detector_distance()
        det_cfg["NbTriggers"] = 1
        det_cfg["CountTime"] = exp_time
        det_cfg["FilenamePattern"] = str(Path(root_dir, f"{path_prefix}_{run_number}"))
        detector.prepare_acquisition(det_cfg)

        #
        # change MD3 phase to data collection mode,
        # this moves in beam stop
        #
        diffractometer.set_phase("DataCollection")

        #
        # open detector cover and fast shutter
        #
        collect.open_detector_cover()
        collect.open_fast_shutter()

        log.info("Sending software trigger to detector.")
        detector.send_software_trigger()
        log.info("Waiting for acquisition to finish.")
        detector.wait_ready()
        log.info("Acquisition is finished.")

    def stop(self):
        super().stop()
        log.info("Aborting acquisition.")
        HWR.beamline.detector.stop_acquisition()

    def post_execute(self):
        super().post_execute()

        #
        # close fast shutter and detector cover
        #
        collect = HWR.beamline.collect
        collect.close_fast_shutter()
        collect.close_detector_cover()
