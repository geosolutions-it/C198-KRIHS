import unittest
import sys

sys.path.append('C:\\OSGeo4W64\\apps\\qgis\\python\\plugins')

from scripts.krihs_import_domains import KhrisXMLDomainsImporterAlgorithm

from scripts.gs_publisher import GeoServerPublisher


class MyTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.sut = KhrisXMLDomainsImporterAlgorithm

    def test_something(self):
        self.assertEqual(True, False)


if __name__ == '__main__':
    unittest.main()
