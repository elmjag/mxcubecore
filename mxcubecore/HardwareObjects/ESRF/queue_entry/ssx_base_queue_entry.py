import os
import logging
import subprocess

from devtools import debug

from mxcubecore import HardwareRepository as HWR
from mxcubecore.queue_entry.base_queue_entry import (
    BaseQueueEntry,
)

import logging
import xmlrpc.client


class SsxBaseQueueEntry(BaseQueueEntry):
    """
    Defines common SSX collection methods.
    """

    def __init__(self, view, data_model):
        super().__init__(view=view, data_model=data_model)
        self.beamline_values = None

        self._use_nicoproc = False
        self._processing_host = "http://lid29control-2:9998"

    def get_data_path(self):
        data_root_path = HWR.beamline.session.get_image_directory(
            os.path.join(
                self._data_model._task_data.path_parameters.subdir,
                self._data_model._task_data.path_parameters.experiment_name,
            )
        )

        process_path = os.path.join(
            HWR.beamline.session.get_base_process_directory(),
            self._data_model._task_data.path_parameters.subdir,
        )

        return data_root_path, process_path

    def take_pedestal_lima2(self, max_freq):
        params = self._data_model._task_data.user_collection_parameters

        exp_time = self._data_model._task_data.user_collection_parameters.exp_time
        sub_sampling = (
            self._data_model._task_data.user_collection_parameters.sub_sampling
        )

        data_root_path, _ = self.get_data_path()

        packet_fifo_depth = 20000

        if params.take_pedestal:
            HWR.beamline.control.safshut_oh2.close()
            if not hasattr(HWR.beamline.control, "lima2_jungfrau_pedestal_scans"):
                HWR.beamline.control.load_script("id29_lima2.py")

            pedestal_dir = HWR.beamline.detector.find_next_pedestal_dir(
                data_root_path, "pedestal"
            )
            logging.getLogger("user_level_log").info(
                f"Storing pedestal in {pedestal_dir}"
            )
            subprocess.Popen(
                "mkdir --parents %s && chmod -R 755 %s" % (pedestal_dir, pedestal_dir),
                shell=True,
                stdin=None,
                stdout=None,
                stderr=None,
                close_fds=True,
            ).wait()

            HWR.beamline.control.lima2_jungfrau_pedestal_scans(
                HWR.beamline.control.lima2_jungfrau4m_rr_smx,
                exp_time,
                max_freq / sub_sampling,
                1000,
                pedestal_dir,
                "pedestal.h5",
                disable_saving="raw",
                print_params=True,
                det_params={"packet_fifo_depth": packet_fifo_depth},
            )

            subprocess.Popen(
                "cd %s && rm -f pedestal.h5 && ln -s %s/pedestal.h5"
                % (data_root_path, pedestal_dir),
                shell=True,
                stdin=None,
                stdout=None,
                stderr=None,
                close_fds=True,
            ).wait()

    def take_pedestal(self, max_freq):
        params = self._data_model._task_data.user_collection_parameters
        exp_time = self._data_model._task_data.user_collection_parameters.exp_time
        sub_sampling = (
            self._data_model._task_data.user_collection_parameters.sub_sampling
        )

        data_root_path, _ = self.get_data_path()

        if params.take_pedestal:
            HWR.beamline.control.safshut_oh2.close()
            if not hasattr(HWR.beamline.control, "jungfrau_pedestal_scans"):
                HWR.beamline.control.load_script("jungfrau.py")

            pedestal_dir = HWR.beamline.detector.find_next_pedestal_dir(
                data_root_path, "pedestal"
            )
            logging.getLogger("user_level_log").info(
                f"Storing pedestal in {pedestal_dir}"
            )
            subprocess.Popen(
                "mkdir --parents %s && chmod -R 755 %s" % (pedestal_dir, pedestal_dir),
                shell=True,
                stdin=None,
                stdout=None,
                stderr=None,
                close_fds=True,
            ).wait()

            HWR.beamline.control.jungfrau_pedestal_scans(
                HWR.beamline.control.jungfrau4m,
                exp_time,
                1000,
                max_freq / sub_sampling,
                pedestal_base_path=pedestal_dir,
                pedestal_filename="pedestal",
            )

        HWR.beamline.control.jungfrau4m.camera.img_src = "GAIN_PED_CORR"

    def start_processing(self, exp_type):
        data_root_path, _ = self.get_data_path()

        if self._use_nicoproc:
            self._start_ssx_processing(
                self.beamline_values,
                self._data_model._task_data,
                data_root_path,
                experiment_type=exp_type,
            )
        else:
            logging.getLogger("user_level_log").info(f"NICOPROC False")

    def prepare_acqiusition(self):
        exp_time = self._data_model._task_data.user_collection_parameters.exp_time
        fname_prefix = self._data_model._task_data.path_parameters.prefix
        num_images = self._data_model._task_data.user_collection_parameters.num_images
        data_root_path, _ = self.get_data_path()

        HWR.beamline.detector.stop_acquisition()
        HWR.beamline.detector.prepare_acquisition(
            num_images, exp_time, data_root_path, fname_prefix
        )
        HWR.beamline.detector.wait_ready()

    def execute(self):
        super().execute()
        debug(self._data_model._task_data)

    def pre_execute(self):
        super().pre_execute()
        self.beamline_values = HWR.beamline.lims.pyispyb.get_current_beamline_values()

    def post_execute(self):
        super().post_execute()

        HWR.beamline.lims.pyispyb.create_ssx_collection(
            self._data_model._task_data,
            self.beamline_values,
        )

        if HWR.beamline.control.safshut_oh2.state.name == "OPEN":
            logging.getLogger("user_level_log").info(f"Opening OH2 safety shutter")
            HWR.beamline.control.safshut_oh2.close()

        HWR.beamline.detector.wait_ready()
        HWR.beamline.detector.stop_acquisition()

    def stop(self):
        super().stop()
        if HWR.beamline.control.safshut_oh2.state.name == "OPEN":
            HWR.beamline.control.safshut_oh2.close()
            logging.getLogger("user_level_log").info("shutter closed")

        HWR.beamline.detector.stop_acquisition()

    def _start_processing(self, dc_parameters, file_paramters):
        param = {
            "exposure": dc_parameters["oscillation_sequence"][0]["exposure_time"],
            "detector_distance": dc_parameters["detectorDistance"],
            "wavelength": dc_parameters["wavelength"],
            "orgx": dc_parameters["xBeam"],
            "orgy": dc_parameters["yBeam"],
            "oscillation_range": dc_parameters["oscillation_sequence"][0]["range"],
            "start_angle": dc_parameters["oscillation_sequence"][0]["start"],
            "number_images": dc_parameters["oscillation_sequence"][0][
                "number_of_images"
            ],
            "image_first": dc_parameters["oscillation_sequence"][0][
                "start_image_number"
            ],
            "fileinfo": file_paramters,
        }

        logging.getLogger("HWR").info("NICOPROC START")

        with xmlrpc.client.ServerProxy(self._processing_host) as p:
            p.start(param)

    def _start_ssx_processing(self, beamline_values, params, path, experiment_type=""):
        param = {
            "exposure": params.user_collection_parameters.exp_time,
            "detector_distance": beamline_values.detector_distance,
            "wavelength": beamline_values.wavelength,
            "orgx": beamline_values.beam_x,
            "orgy": beamline_values.beam_y,
            "oscillation_range": params.collection_parameters.osc_range,
            "start_angle": params.collection_parameters.osc_start,
            "number_images": params.user_collection_parameters.num_images,
            "image_first": params.collection_parameters.first_image,
            "fileinfo": params.path_parameters.dict(),
            "root_path": path,
            "experiment_type": experiment_type,
        }

        logging.getLogger("HWR").info("NICOPROC START")

        try:
            with xmlrpc.client.ServerProxy(self._processing_host) as p:
                p.start(param)
        except Exception:
            logging.getLogger("HWR").exception("")

    def _stop_processing(self):
        logging.getLogger("HWR").info("NICOPROC STOP")

        with xmlrpc.client.ServerProxy(self._processing_host) as p:
            p.stop()
