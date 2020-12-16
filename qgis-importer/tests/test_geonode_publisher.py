import unittest
import sys
from collections import namedtuple
from unittest.mock import MagicMock, patch

sys.path.append('C:\\OSGeo4W64\\apps\\qgis\\python\\plugins')

from scripts.geonode_publisher import GeoNodePublisher, QgsProcessingFeedback


class MyTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.sut = GeoNodePublisher()
        self.example_layer = namedtuple("Layer", ["title"])
        self.example_layer.name = "my_layer_title"
        self.successful_request = namedtuple("Response", ["status_code"])
        self.successful_request.status_code = 200
        self.parameters = {
            'GEONODE_REST_URL': 'http://localhost:8080/api/v2/management/',
            'GS_REST_URL': 'http://localhost:8080/geoserver/rest/',
            'COMMAND': '',
            'GEONODE_USERNAME': 'admin',
            'GEONODE_PASSWORD': 'geonode',
            'DB_NAME': 'KRIHS',
            'GS_ADMIN': 'admin',
            'GS_PASSWORD': 'geoserver',
            'GS_STORE_NAME': None,
            'GS_WORKSPACE': None
        }
        self.sut.fetch_layers_from_geoserver = MagicMock()

    def test_sut_correclty_initiate(self):
        self.assertEqual(GeoNodePublisher, type(self.sut.createInstance()))

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
        expected = [self.example_layer.name]
        actual = self.sut.processAlgorithm(self.parameters, {}, QgsProcessingFeedback())
        self.assertListEqual(expected, actual)


if __name__ == '__main__':
    unittest.main()
