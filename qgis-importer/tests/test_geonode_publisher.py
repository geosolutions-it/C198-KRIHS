import unittest
import sys
from collections import namedtuple
from unittest.mock import MagicMock, patch

from PyQt5.QtWidgets import QApplication

sys.path.append('C:\\OSGeo4W64\\apps\\qgis\\python\\plugins')

from scripts.geonode_publisher import GeoNodeSynchronizer, QgsProcessingFeedback, QgsApplication

app = QApplication([])
qgs = QgsApplication([], False)
qgs.setPrefixPath("C:\\OSGeo4W64\\apps\\qgis", True)
qgs.initQgis()


class MyTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.sut = GeoNodeSynchronizer()
        self.example_layer = namedtuple("Layer", ["name"])
        self.example_layer.name = "c:my_layer_title"
        self.successful_request = namedtuple("Response", ["status_code"])
        self.successful_request.status_code = 200
        self.parameters = { "GEONODE_AUTH_ID": 'k51x6pn', "GEONODE_REST_URL": 'http://localhost:8000/api/v2/management/updatelayers/', "GS_ADMIN": 'admin', "GS_PASSWORD": 'geoserver', "GS_REST_URL": 'http://localhost:8080/geoserver/rest/', "GS_STORE_NAME": 'krihs_ds', "GS_WORKSPACE": 'krihs_ws' }
        self.sut.fetch_layers_from_geoserver = MagicMock()
        self.sut.get_credentials = MagicMock()

    def test_sut_correclty_initiate(self):
        self.assertEqual(GeoNodeSynchronizer, type(self.sut.createInstance()))

    def test_sut_groupId_is_the_expected_one(self):
        self.assertEqual("krihs", self.sut.groupId())

    def test_sut_group_is_the_expected_one(self):
        self.assertEqual("krihs", self.sut.group())

    def test_sut_displayName_is_the_expected_one(self):
        self.assertEqual("GeoNode Synchronizer", self.sut.displayName())

    def test_sut_name_is_the_expected_one(self):
        self.assertEqual("GeoNodePublisher", self.sut.name())

    @patch("requests.post")
    def test_sut_processAlgorithm_should_produce_the_expected_output(self, mocked_post_request):
        mocked_post_request.return_value = self.successful_request
        self.sut.fetch_layers_from_geoserver.return_value = [self.example_layer]
        self.sut.get_credentials.return_value = {"username": "abc", "password": "cde"}
        actual = self.sut.processAlgorithm(self.parameters, {}, QgsProcessingFeedback())
        self.assertEqual({}, actual)


if __name__ == '__main__':
    unittest.main()
