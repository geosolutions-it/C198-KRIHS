import unittest
import sys
from collections import namedtuple
from unittest.mock import MagicMock, patch

sys.path.append('C:\\OSGeo4W64\\apps\\qgis\\python\\plugins')

from scripts.geonode_publisher import GeoNodeSynchronizer, QgsProcessingFeedback


class MyTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.sut = GeoNodeSynchronizer()
        self.example_layer = namedtuple("Layer", ["name"])
        self.example_layer.name = "c:my_layer_title"
        self.successful_request = namedtuple("Response", ["status_code"])
        self.successful_request.status_code = 200
        self.parameters = { "GEONODE_PASSWORD": 'admin', "GEONODE_REST_URL": 'http://localhost:8000/api/v2/management/updatelayers/', "GEONODE_USERNAME": 'admin', "GS_ADMIN": 'admin', "GS_PASSWORD": 'geoserver', "GS_REST_URL": 'http://localhost:8080/geoserver/rest/', "GS_STORE_NAME": 'krihs_ds', "GS_WORKSPACE": 'krihs_ws' }

    def test_sut_correclty_initiate(self):
        self.assertEqual(GeoNodeSynchronizer, type(self.sut.createInstance()))

    def test_sut_groupId_is_the_expected_one(self):
        self.assertEqual("krihs", self.sut.groupId())

    def test_sut_group_is_the_expected_one(self):
        self.assertEqual("krihs", self.sut.group())

    def test_sut_displayName_is_the_expected_one(self):
        self.assertEqual("GeoNode Publisher", self.sut.displayName())

    def test_sut_name_is_the_expected_one(self):
        self.assertEqual("GeoNodePublisher", self.sut.name())

    @patch("requests.post")
    def test_sut_processAlgorithm_should_produce_the_expected_output(self, mocked_post_request):
        mocked_post_request.return_value = self.successful_request
        self.sut.fetch_layers_from_geoserver.return_value = [self.example_layer]
        actual = self.sut.processAlgorithm(self.parameters, {}, QgsProcessingFeedback())
        self.assertEqual({}, actual)


if __name__ == '__main__':
    unittest.main()
