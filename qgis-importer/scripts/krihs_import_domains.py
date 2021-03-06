"""
Name : KhrisXMLDomainsImporterAlgorithm
Group : krihs
"""
from xml.dom.minidom import parse
from qgis.core import QgsProcessing
from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterString
from qgis.core import QgsProcessingParameterBoolean
import processing
import xml.dom.minidom

TAG_ROOT = "esri:Workspace"
TAG_WORKSPACE_DEF = "WorkspaceDefinition"
TAG_DOMAINS = "Domains"
TAG_DOMAIN = "Domain"
TAG_DOMAIN_NAME = "DomainName"
TAG_DOMAIN_FIELDTYPE = "FieldType"
TAG_DOMAIN_CODEDVALUES = "CodedValues"
TAG_DOMAIN_CVALUE = "CodedValue"
TAG_DOMAIN_CVALUE_NAME = "Name"
TAG_DOMAIN_CVALUE_CODE = "Code"


class KhrisXMLDomainsImporterAlgorithm(QgsProcessingAlgorithm):
    """
    Custom algorithm to import domains table defined in a XML Workspace definition of a ESRI geodatabase
    into a PostGIS database
    """

    def initAlgorithm(self, config=None):
        """
        Initialize the algorithm.
        It accepts the following parameters (via QGIS processing):
        - XMLPATH: path to the Xml Workspace definition of the geodatabase (for the geopackage to import)
        - DBNAME: name of the database as defined in QGIS PG connection (default is 'KRIHS')
        - SCHEMA: name of the destination schema (default is 'public')
        - DROPIFEXISTS: name of the destination schema (default is 'public')
        :param config:
        :return:
        """
        self.addParameter(QgsProcessingParameterString('XMLPATH', 'XML Workspace Definition', multiLine=False, defaultValue=''))
        self.addParameter(QgsProcessingParameterString('DBNAME', 'Pg Connection Name', multiLine=False, defaultValue='KRIHS'))
        self.addParameter(QgsProcessingParameterString('SCHEMA', 'Schema', multiLine=False, defaultValue='public'))
        self.addParameter(QgsProcessingParameterBoolean('DROPIFEXISTS', 'Drop if exists', optional=True, defaultValue=True))

    def getDomains(self):
        """
        Return a list of domains
        :return:
        """
        DOMTree = xml.dom.minidom.parse(self.xml_path)
        collection = DOMTree.documentElement
        wrkDef = collection.getElementsByTagName(TAG_WORKSPACE_DEF)[0]
        domains = wrkDef.getElementsByTagName(TAG_DOMAINS)[0]
        domain_list = domains.getElementsByTagName(TAG_DOMAIN)
        return domain_list

    def getDomainDef(self, domain):
        """
        Return the definition of the domain as array with the following information:
        - [0]: name of the domain
        - [1]: SQL syntax to define the Domain Table in PostGIS
        - [2]: number of rows in the domain
        :param domain: dom node of the domain to analyze
        :return:
        """
        name = domain.getElementsByTagName(TAG_DOMAIN_NAME)[0].childNodes[0].data
        type = domain.getElementsByTagName(TAG_DOMAIN_FIELDTYPE)[0].childNodes[0].data 
        ftype = "VARCHAR(255)"
        if type != "esriFieldTypeString":
            ftype = "SMALLINT"
        values = domain.getElementsByTagName(TAG_DOMAIN_CODEDVALUES)[0]
        value_list = values.getElementsByTagName(TAG_DOMAIN_CVALUE)
        sql = ""
        if self.pg_drop_before:
            sql_drop = "DROP TABLE IF EXISTS %s.%s CASCADE;" % (self.pg_schema, name.lower())
            sql += sql_drop
        sql_create = "CREATE TABLE %s.%s(name VARCHAR(255), code %s, PRIMARY KEY(code));" % (self.pg_schema, name.lower(), ftype)
        sql += sql_create
        rows = 0
        for cvalue in value_list:
            cvalue_name = cvalue.getElementsByTagName(TAG_DOMAIN_CVALUE_NAME)[0].childNodes[0].data
            cvalue_code_nodes = cvalue.getElementsByTagName(TAG_DOMAIN_CVALUE_CODE)[0].childNodes
            cvalue_code = ""
            if len(cvalue_code_nodes)>0:
                cvalue_code = cvalue_code_nodes[0].data  
            sql_insert = "INSERT INTO %s.%s(name, code) VALUES (" % (self.pg_schema, name.lower())
            if type == "esriFieldTypeInteger":
                sql_insert += "'%s', %s);" % (cvalue_name.replace("'", "''"), cvalue_code)
            else:
                sql_insert += "'%s', '%s');" % (cvalue_name.replace("'", "''"), cvalue_code.replace("'", "''"))
            sql += sql_insert
            rows += 1
        return [name, sql, rows] 

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
        self.xml_path = parameters["XMLPATH"]
        if not self.xml_path.lower().endswith(".xml"):
            feedback = QgsProcessingMultiStepFeedback(0, model_feedback)
            feedback.reportError("XML Workspace Definition is not an XML file!", True)
            return {}
        self.pg_conn_name = parameters["DBNAME"]
        self.pg_schema = parameters["SCHEMA"]
        self.pg_drop_before = parameters["DROPIFEXISTS"]
        domain_list = self.getDomains()
        feedback = QgsProcessingMultiStepFeedback(1+len(domain_list), model_feedback)        
        step=0
        for domain in domain_list:
            step+=1
            definition = self.getDomainDef(domain)
            try:
                alg_params = {
                    'DATABASE': self.pg_conn_name,
                    'SQL': definition[1]
                }
                processing.run(
                    'qgis:postgisexecutesql',
                    alg_params, context=context, feedback=feedback, is_child_algorithm=True)
                feedback.pushInfo("Domain: " + definition[0])
                feedback.pushInfo("   SQL: " + definition[1])
                feedback.pushInfo("   Rows: " + str(definition[2]))
            except Exception as e:
                feedback.reportError("Error importing domain " + definition[0] + ": " + str(e), False)
            feedback.setCurrentStep(step)
        results = {}
        outputs = {}
        return results

    def name(self):
        """
        Name of the algorithm
        :return:
        """
        return 'KhrisXMLDomainsImporterAlgorithm'

    def displayName(self):
        """
        Name to display for the algorithm in QGIS
        :return:
        """
        return 'XML Domains Importer'

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
        return KhrisXMLDomainsImporterAlgorithm()
