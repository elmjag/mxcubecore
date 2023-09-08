"""
A client for ISPyB Webservices.
"""
import logging
import json
import cgi

from datetime import datetime
from requests import post, get
from urllib.parse import urljoin

from mxcubecore import HardwareRepository as HWR
from ISPyBRestClient import ISPyBRestClient


class MAXIVISPyBRestClient(ISPyBRestClient):
    """
    RESTful Web-service client for EXI.
    MAX IV uses different url for ispyb root and exi
    """

    def __init__(self, *args):
        ISPyBRestClient.__init__(self, *args)

    def init(self):
        ISPyBRestClient.init(self)
        self.exi_root = self.get_property("exi_root").strip()

    def dc_link(self, did):
        """
        Get the LIMS link the data collection with id <id>.

        :param str did: Data collection ID
        :returns: The link to the data collection
        """
        url = "#"
        if self.exi_root is not None and did:
            path = "mx/index.html#/mx/datacollection/proposal/{pcode}{pnumber}/dcid/{did}/main"
            path = path.format(pcode=HWR.beamline.session.proposal_code,
                               pnumber=HWR.beamline.session.proposal_number,
                               did=did)

            url = urljoin(self.exi_root, path)

        else:
            return self.dc_list_link()

        return url

    def dc_list_link(self):
        """
        Get the LIMS link the data collection with id <id>.

        :param str did: Data collection ID
        :returns: The link to the data collection
        """
        url = "#"
        if self.exi_root is not None and HWR.beamline.session.session_id:
            path = "mx/index.html#/mx/datacollection/session/{session_id}/main"
            path = path.format(session_id=HWR.beamline.session.session_id)

            url = urljoin(self.exi_root, path)

        return url

    def get_energyscan_plot(self, escan_id):
        """
        Get the image data for energy scan with id <escan_id>

        :param int escan_id: The energy scan id
        :returns: tuple on the form (file name  , base64 encoded data)
        """
        self._ISPyBRestClient__update_rest_token()
        fname, data = ('', '')
        url = "{rest_root}{token}"
        url += "/proposal/{pcode}{pnumber}/mx/energyscan/energyscanId/{escan_id}/jpegchooch"
        url = url.format(rest_root=self._ISPyBRestClient__rest_root,
                         token=str(self._ISPyBRestClient__rest_token),
                         pcode=HWR.beamline.session.proposal_code,
                         pnumber=HWR.beamline.session.proposal_number,
                         escan_id=escan_id)
        try:
            response = get(url)
            data = response.content
            value, params = cgi.parse_header(response.headers)
            fname = params['filename']
        except:
            response = []
            logging.getLogger("ispyb_client").warning("Cannot retrieve Energy Scan plot")

        return fname, data

    def get_xrf_plot(self, xrf_id):
        """
        Get the image data for energy scan with id <escan_id>

        :param int escan_id: The energy scan id
        :returns: tuple on the form (file name  , base64 encoded data)
        """
        self._ISPyBRestClient__update_rest_token()
        fname, data = ('', '')
        url = "{rest_root}{token}"
        url += "/proposal/{pcode}{pnumber}/mx/xrfscan/xrfscanId/{xrf_id}/image/jpegScanFileFullPath/get"
        url = url.format(rest_root=self._ISPyBRestClient__rest_root,
                         token=str(self._ISPyBRestClient__rest_token),
                         pcode=HWR.beamline.session.proposal_code,
                         pnumber=HWR.beamline.session.proposal_number,
                         xrf_id=xrf_id)
        try:
            response = get(url)
            data = response.content
            value, params = cgi.parse_header(response.headers)
            fname = params['filename']
        except:
            logging.getLogger("ispyb_client").warning("Cannot retrieve XRF plot")

        return fname, data
