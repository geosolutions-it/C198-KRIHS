import os
from qgis.core import *
from geoserver.catalog import Catalog
import xml.dom.minidom


TAG_WORKSPACE_DEF = "WorkspaceDefinition"
TAG_DATASETDEFINITIONS = "DatasetDefinitions"
TAG_DE = "DataElement"
TAG_DE_NAME = "Name"
TAG_DE_TYPE = "DatasetType"


TAG_ROOT = "esri:Workspace"
TAG_DE_FIELDS = "Fields"
TAG_DE_FIELDS_ARR = "FieldArray"
TAG_DE_FIELD = "Field"
TAG_DE_FIELD_NAME = "Name"
TAG_DE_FIELD_TYPE = "Type"
TAG_DE_FIELD_ISNULL = "IsNullable"
TAG_DE_FIELD_LENGTH = "Length"
TAG_DE_FIELD_PRECISION = "Precision"
TAG_DE_FIELD_SCALE = "Scale"
TAG_DE_FIELD_DOMAIN = "Domain"
TAG_DE_FIELD_DOMAIN_NAME = "DomainName"
TAG_DE_SUBTYPE = "SubtypeFieldName"
TAG_DE_SUBTYPE_DEF = "DefaultSubtypeCode"
TAG_DE_SUBTYPES = "Subtypes"
TAG_DE_SUBTYPES_SUBTYPE = "Subtype"
TAG_DE_GEOM_DEF = "GeometryDef"
TAG_DE_GEOM_TYPE = "GeometryType"
TAG_DE_GEOM_Z = "HasZ"
TAG_DE_GEOM_M = "HasM"
TAG_DE_GEOM_SPATIAL_REF = "SpatialReference"
TAG_DE_GEOM_WKID = "WKID"


class GeoServerPublisher(QgsProcessingAlgorithm):
    """
    Algorithm to define and import feature classes from geopackage and EXRI Xml Workspace definition into PostGIS
    """

    def initAlgorithm(self, config=None):
        """
        Initialize the algorithm.
        It accepts the following parameters (via QGIS processing):
        - XML_PATH: path to the Xml Workspace definition of the geodatabase (for the geopackage to import)
        - DB_NAME: name of the database as defined in QGIS PG connection (default is 'KRIHS')
        - GS_REST_URL: GeoServer ReST url (default 'http://localhost:8080/geoserver/rest/')
        - GS_ADMIN: GeoServer Admin user (default 'admin')
        - GS_PASSWORD: GeoServer Admin password (default 'geoserver')
        - GS_STORE: name of the GeoServer PostGIS datastore (default is as <DBNAME>_DS)
        - GS_WORKSPACE: name of the GeoServer Workspace (default is <DBNAME>_WS)
        """
        self.addParameter(
            QgsProcessingParameterString('XML_PATH', 'XML Workspace Definition', multiLine=False, defaultValue=''))
        self.addParameter(
            QgsProcessingParameterString('DB_NAME', 'Pg Connection Name', multiLine=False, defaultValue='KRIHS'))
        self.addParameter(
            QgsProcessingParameterString('GS_REST_URL', 'GS ReST address', multiLine=False, defaultValue='http://localhost:8080/geoserver/rest/'))
        self.addParameter(
            QgsProcessingParameterString('GS_ADMIN', 'GS Admin user', multiLine=False, defaultValue='admin'))
        self.addParameter(
            QgsProcessingParameterString('GS_PASSWORD', 'GS Admin password', multiLine=False, defaultValue='geoserver'))
        self.addParameter(
            QgsProcessingParameterString('GS_STORE', 'GS Datastore Name', multiLine=False, defaultValue=None))
        self.addParameter(
            QgsProcessingParameterString('GS_WORKSPACE', 'GS Workspace Name', multiLine=False, defaultValue=None))

    def getDatasets(self):
        """
        Returns the datasets from the XML workspace definition
        :return:
        """
        DOMTree = xml.dom.minidom.parse(self.xml_path)
        collection = DOMTree.documentElement
        wrkDef = collection.getElementsByTagName(TAG_WORKSPACE_DEF)[0]
        datasetDefs = wrkDef.getElementsByTagName(TAG_DATASETDEFINITIONS)[0]
        dataset_list = datasetDefs.getElementsByTagName(TAG_DE)
        return dataset_list

    def get_db_params(self, db_name):
        qs = QgsSettings()
        qs_pg_prefix = "PostgreSQL/connections/" + db_name + "/"
        return dict(
            host=qs.value(qs_pg_prefix + "host"),
            port=qs.value(qs_pg_prefix + "port"),
            dbtype="postgis",
            database=qs.value(qs_pg_prefix + "database"),
            user=qs.value(qs_pg_prefix + "username"),
            passwd=qs.value(qs_pg_prefix + "password"),
        )

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
        self.xml_path = parameters["XML_PATH"]
        if not self.xml_path.lower().endswith(".xml"):
            feedback = QgsProcessingMultiStepFeedback(0, model_feedback)
            feedback.reportError("XML Workspace Definition is not an XML file!", True)
            return {}

        db_name = parameters["DB_NAME"]
        db_params = self.get_db_params(db_name)
        store_name = parameters["GS_STORE"]
        wrk_name = parameters["GS_WORKSPACE"]

        dataset_list = []
        datasets = self.getDatasets()
        for dataset in datasets:
            type = dataset.getElementsByTagName(TAG_DE_TYPE)[0].childNodes[0].data
            if type == "esriDTFeatureClass":
                ds_name = dataset.getElementsByTagName(TAG_DE_NAME)[0].childNodes[0].data
                dataset_list.append({
                    "name": ds_name.lower(),
                    "srs": "EPSG:4326"
                })

        feedback = QgsProcessingMultiStepFeedback(2 + len(dataset_list), model_feedback)

        feedback.pushInfo("Get GeoServer Catalog: " + parameters["GS_REST_URL"])
        gs_catalogue = Catalog(parameters["GS_REST_URL"], parameters["GS_ADMIN"], parameters["GS_PASSWORD"])

        # workspace
        if wrk_name == "" or wrk_name is None:
            wrk_name = db_name.lower() + "_ws"
        wrk_uri = "http://" + wrk_name
        feedback.pushInfo("GeoServer Workspace: " + wrk_name + " (" + wrk_uri + ")")
        workspace = gs_catalogue.get_workspace(wrk_name)
        if workspace is None:
            workspace = gs_catalogue.create_workspace(wrk_name, wrk_uri)
        feedback.setCurrentStep(1)

        # store
        if store_name == "" or store_name is None:
            store_name = db_name.lower() + "_ds"
        feedback.pushInfo("GeoServer Data Store: " + store_name)
        store = gs_catalogue.get_store(store_name, workspace)
        if store is None:
            store = gs_catalogue.create_datastore(store_name, workspace)
            store.connection_parameters.update(**db_params)
            gs_catalogue.save(store)
        feedback.setCurrentStep(2)

        step = 2
        published_count = 0
        for ds_cur in dataset_list:
            feedback.pushInfo("GeoServer Publish: " + ds_cur["name"] + " (" + ds_cur["srs"] + ")")
            try:
                gs_catalogue.publish_featuretype(ds_cur["name"], store, ds_cur["srs"])
                published_count += 1
            except Exception as e:
                feedback.reportError("Error: " + str(e), False)
            step += 1
            feedback.setCurrentStep(step)

        layers = gs_catalogue.get_layers(store)
        feedback.pushInfo("-"*80)
        feedback.pushInfo("Published layers: " + str(published_count))
        for layer in layers:
            feedback.pushInfo(layer.name + " is published!")
        feedback.pushInfo("-" * 80)
        results = {}
        outputs = {}
        return results

    def name(self):
        """
        Name of the algorithm
        :return:
        """
        return 'GeoServerPublisher'

    def displayName(self):
        """
        Name to display for the algorithm in QGIS
        :return:
        """
        return 'GeoServer Publisher'

    def group(self):
        """
        Name of the group for this script
        :return:
        """
        return 'krihs'

    def groupId(self):
        """
        Identifier for the group
        """
        return 'krihs'

    def createInstance(self):
        """
        Create the algorithm instance
        :return:
        """
        return GeoServerPublisher()
