import unittest
import sys

sys.path.append('C:\\OSGeo4W64\\apps\\qgis\\python\\plugins')

from scripts.geonode_publisher import GeoNodePublisher


class MyTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.sut = GeoNodePublisher()

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

    def test_sut_processAlgorithm_should_produce_the_expected_output(self):
        x = self.sut.processAlgorithm()
        print(x)
        self.assertTrue(False)


if __name__ == '__main__':
    unittest.main()
