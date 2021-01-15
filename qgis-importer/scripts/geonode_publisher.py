import requests
from geoserver.catalog import Catalog
from qgis.core import *
from requests.auth import HTTPBasicAuth


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
                                         defaultValue='http://localhost:8000/api/v2/management/'))
        self.addParameter(
            QgsProcessingParameterString('GS_REST_URL', 'GS ReST address', multiLine=False,
                                         defaultValue='http://localhost:8080/geoserver/rest/'))
        self.addParameter(
            QgsProcessingParameterString('GEONODE_AUTH_ID', 'GeoNode Authentication id', multiLine=False, defaultValue='GeoNode'))
        self.addParameter(
            QgsProcessingParameterString('GS_AUTH_ID', 'GS Authentication id', multiLine=False, defaultValue='admin'))
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

        parameters['GS_STORE_NAME'] = parameters.get('GS_STORE_NAME', None) or 'krihs_ds'
        parameters['GS_WORKSPACE'] = parameters.get('GS_WORKSPACE', None) or 'krihs_ws'

        feedback = QgsProcessingMultiStepFeedback(0, model_feedback)
        feedback.pushInfo("Get GeoServer Catalog: " + parameters["GS_REST_URL"])

        layers = self.fetch_layers_from_geoserver(parameters)
        feedback.pushInfo(
            f"The following layers are sent to Geonode: {[x.name for x in layers]} at {parameters['GEONODE_REST_URL']}"
        )

        credentials = get_credentials(parameters['GEONODE_AUTH_ID'])

        auth = HTTPBasicAuth(
            credentials["username"], credentials["password"]
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

            result = requests.post(url=f'{parameters["GEONODE_REST_URL"]}updatelayers/', auth=auth, json=json_to_send, headers=headers, verify=False)
            if result.status_code == 200:
                feedback.pushInfo(f"Request for layer {layer_name} successfuly sent")
            else:
                print(result.json())
                feedback.reportError(
                    f"Error during processing request for layer {layer.name} with error: {result.json()}"
                )

        feedback.pushInfo("Layers processing completed")
        return {}

    @staticmethod
    def fetch_layers_from_geoserver(parameters):
        store_name = parameters["GS_STORE_NAME"]
        workspace = parameters["GS_WORKSPACE"]

        gs_credentials = get_credentials(parameters['GS_AUTH_ID'])

        gs_catalogue = Catalog(
            parameters["GS_REST_URL"], gs_credentials['username'], gs_credentials['password'], validate_ssl_certificate=False
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


def get_credentials(auth_id):
    auth_mgr = QgsApplication.authManager()
    auth_cfg = QgsAuthMethodConfig()
    auth_mgr.loadAuthenticationConfig(auth_id, auth_cfg, True)
    return auth_cfg.configMap()
