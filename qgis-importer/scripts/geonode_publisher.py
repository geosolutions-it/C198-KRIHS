from qgis.core import *
from geoserver.catalog import Catalog
import requests
from requests.auth import HTTPBasicAuth
import json


class GeoNodeSynchronizer(QgsProcessingAlgorithm):
    """
    Algorithm to define and import feature classes from geopackage and EXRI Xml Workspace definition into PostGIS
    """

    def initAlgorithm(self, config=None):
        """
        Initialize the algorithm.
        It accepts the following parameters (via QGIS processing):
        - GEONODE_REST_URL: GeoServer ReST url (default 'http://localhost:8080/api/v2/management/')
        - COMMAND: name of command to execute on GeoNode
        - GEONODE_USER: GeoNode username (default 'admin')
        - GEONODE_PASSWORD: GeoNode username password (default 'geoserver')
        """
        self.addParameter(
            QgsProcessingParameterString('GEONODE_REST_URL', 'GeoNode REST address', multiLine=False,
                                         defaultValue='http://localhost:8000/api/v2/management/updatelayers'))
        self.addParameter(
            QgsProcessingParameterString('GS_REST_URL', 'GS ReST address', multiLine=False,
                                         defaultValue='http://localhost:8080/geoserver/rest/'))
        self.addParameter(
            QgsProcessingParameterString('GEONODE_USERNAME', 'GeoNode API user', multiLine=False, defaultValue='admin'))
        self.addParameter(
            QgsProcessingParameterString('GEONODE_PASSWORD', 'GeoNode API password', multiLine=False,
                                         defaultValue='admin'))
        self.addParameter(
            QgsProcessingParameterString('GS_ADMIN', 'GS Admin user', multiLine=False, defaultValue='admin'))
        self.addParameter(
            QgsProcessingParameterString('GS_PASSWORD', 'GS Admin password', multiLine=False, defaultValue='geoserver'))
        self.addParameter(
            QgsProcessingParameterString('GS_STORE_NAME', 'GS Datastore Name', multiLine=False, defaultValue="krihs_ds"))
        self.addParameter(
            QgsProcessingParameterString('GS_WORKSPACE', 'GS Workspace Name', multiLine=False, defaultValue="krihs_ws"))

    def processAlgorithm(self, parameters, context, model_feedback):
        """
        Process the algorithm
        :param parameters: parameters of the process
        :param context: context of the process
        :param model_feedback: feedback instance for the process
        :return:
        """
        # Use a multi-step feedback, so that individual child algorithm progress reports are adjusted for the
        # overall progress through the model

        feedback = QgsProcessingMultiStepFeedback(0, model_feedback)
        feedback.pushInfo("Get GeoServer Catalog: " + parameters["GS_REST_URL"])

        layers = self.fetch_layers_from_geoserver(parameters)
        feedback.pushInfo(
            f"The following layers are sent to Geonode: {[x.name for x in layers]} at {parameters['GEONODE_REST_URL']}"
        )

        auth = HTTPBasicAuth(
            parameters["GEONODE_USERNAME"], parameters["GEONODE_PASSWORD"]
        )

        feedback.pushInfo(f"Param used {parameters}")

        headers = {'Content-Type': 'application/json'}
        for layer in layers:
            layer_name = layer.name.split(":")[1]
            feedback.pushInfo(f"Start processing layer {layer_name}")
            json_to_send = {
                "kwargs": {
                    "store": parameters["GS_STORE_NAME"],
                    "workspace": parameters["GS_WORKSPACE"],
                    "filter": layer_name,
                }
            }
            feedback.pushInfo(f"Start processing layer {json_to_send}")

            result = requests.post(url=parameters["GEONODE_REST_URL"], auth=auth, json=json_to_send, headers=headers)
            if result.status_code == 200:
                feedback.pushInfo(f"Request for layer {layer_name} successfuly sent")
            else:
                feedback.reportError(
                    f"Error during processing request for layer {layer.name}"
                )

        feedback.pushInfo("Layers processing completed")
        return {}

    @staticmethod
    def fetch_layers_from_geoserver(parameters):
        store_name = parameters["GS_STORE_NAME"]
        workspace = parameters["GS_WORKSPACE"]

        gs_catalogue = Catalog(
            parameters["GS_REST_URL"], parameters["GS_ADMIN"], parameters["GS_PASSWORD"]
        )
        resources = gs_catalogue.get_resources(stores=store_name, workspaces=workspace)
        layers = []
        for resource in resources:
            layer = gs_catalogue.get_layers(resource)
            layers += layer
        return layers


    def name(self):
        """
        Name of the algorithm
        :return:
        """
        return "GeoNodePublisher"

    def displayName(self):
        """
        Name to display for the algorithm in QGIS
        :return:
        """
        return "GeoNode Synchronizer"

    def group(self):
        """
        Name of the group for this script
        :return:
        """
        return "krihs"

    def groupId(self):
        """
        Identifier for the group
        """
        return "krihs"

    def createInstance(self):
        """
        Create the algorithm instance
        :return:
        """
        return GeoNodeSynchronizer()
