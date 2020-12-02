"""
Name : modello
Group :
"""
from xml.dom.minidom import parse
from qgis.core import QgsProcessing
from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterString
from qgis.core import QgsProcessingParameterBoolean
from qgis.core import QgsVectorLayer
import processing
import xml.dom.minidom

TAG_ROOT = "esri:Workspace"
TAG_WORKSPACE_DEF = "WorkspaceDefinition"
TAG_DATASETDEFINITIONS = "DatasetDefinitions"
TAG_DE = "DataElement"
TAG_DE_NAME = "Name"
TAG_DE_TYPE = "DatasetType"
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


class Field:
    """
    This class map the ESRI definition of a field and allows us to convert into a PostGIS data type
    """
    def __init__(self):
        """
        Constructor
        """
        self.domain = None
        self.name = None
        self.type = None
        self.isnull = True
        self.length = None
        self.precision = None
        self.scale = None
        self.geom_def = None
        self.default = None
        self.serial = False

    def is_valid(self):
        """
        Returns if the field is valid
        :return:
        """
        if self.name is not None and self.to_pg_type() is not None:
            if self.name.lower() not in ('shape_length', 'shape_area', 'globalid'):
                return True
        return False

    def is_geometry(self):
        """
        Returns if it is a geometry field
        :return:
        """
        return self.name.lower() == 'shape' and self.type == "esriFieldTypeGeometry"

    def to_pg_type(self):
        """
        Convert the ESRI field to a PostgreSQL definition
        :return:
        """
        if self.type == "esriFieldTypeSmallInteger": 
            return "SMALLINT"
        elif self.type == "esriFieldTypeInteger":
            return "INTEGER"
        elif self.type in ("esriFieldTypeDouble", "esriFieldTypeSingle"):    
            if self.precision == 0 and self.scale == 0:
                if self.type == "esriFieldTypeDouble":
                    return "DOUBLE PRECISION"
                elif self.type == "esriFieldTypeSingle":
                    return "REAL"
            else:
                return "NUMERIC(%s, %s)" % (str(self.precision), str(self.scale))
        elif self.type == "esriFieldTypeString":
            leng = 255
            if self.length is not None:
                leng = self.length
            return "VARCHAR(%s)" % (str(leng),)
        elif self.type == "esriFieldTypeDate":
            return "TIMESTAMP"
        elif self.type == "esriFieldTypeOID":
            return "BIGINT"
        elif self.type == "esriFieldTypeGlobalID":
            return "VARCHAR(32)"
        else:
            return None

    def geom_info(self):
        """
        Return the geometry definition as dictionary with the following keys:
        - type: geometry type
        - dim: dimension of the geometry (2, 3 or 4)
        - epsg: EPSG of the geometry field
        - gtype: geometry type value as expected by the qgis:importvectorintopostgisdatabaseavailableconnections
        algorithm
        :return:
        """
        ret = {'type': "POINT", 'dim': 2, 'epsg': 4326, 'gtype': 3}
        g_type = self.geom_def.getElementsByTagName(TAG_DE_GEOM_TYPE)[0].childNodes[0].data
        type == "POINT"
        if g_type == "esriGeometryPolygon":
            ret["type"] = "MULTIPOLYGON"
            ret["gtype"] = 8
        elif g_type == "esriGeometryPolyline":
            ret["type"] = "MULTILINESTRING"
            ret["gtype"] = 9
        elif g_type == "esriGeometryMultiPoint":
            ret["type"] = "MULTIPOINT"
            ret["gtype"] = 7
        g_z = self.geom_def.getElementsByTagName(TAG_DE_GEOM_Z)[0].childNodes[0].data
        g_m = self.geom_def.getElementsByTagName(TAG_DE_GEOM_M)[0].childNodes[0].data
        if g_z == "true":
            ret["dim"] += 1
        if g_m == "true":
            ret["dim"] += 1
        g_srs = self.geom_def.getElementsByTagName(TAG_DE_GEOM_SPATIAL_REF)[0]  
        ret["epsg"] = int(g_srs.getElementsByTagName(TAG_DE_GEOM_WKID)[0].childNodes[0].data)      
        return ret

    def has_domain(self):
        """
        Returns if the field has an associated domain
        :return:
        """
        return self.domain is not None

    def __str__(self):
        """
        String representation of the object
        :return:
        """
        if self.serial:
            sql = self.name.lower() + " SERIAL"
        else:        
            s_null = "NOT NULL"
            if self.isnull == "true":
                s_null = "NULL"
            s_default = ""
            if self.default is not None:
                if self.type == "esriFieldTypeString":
                    s_default = "DEFAULT '%s'" % (self.default.replace("'", "''"),)
                else:
                    s_default = "DEFAULT %s" % (self.default,)
            sql = "%s %s %s %s" % (self.name.lower(), self.to_pg_type(), s_null, s_default)
        return sql


class FeatureClass:
    """
    This class map the ESRI definition of a Feature Class and allows us to convert into a PostGIS Table
    """
    def __init__(self, name, oid=None, sub_type=None, sub_type_default=None, schema='public'):
        """
        Constructor
        :param name: name of the feature class
        :param oid: oid of the feature class
        :param sub_type: name of the field used to define subtypes in the feature class
        :param sub_type_default: default value for the subtype field
        :param schema: name of the destination schema
        """
        self.schema = schema
        self.name = name
        self.oid = oid
        if sub_type == '':
            sub_type = None
            sub_type_default = None
        self.sub_type = sub_type
        self.sub_type_default = sub_type_default
        self.fields = []  
        self.geom = None  
        self.subtypes = []    
    
    def add_field(self, field):
        """
        Add a field into the fields list
        :param field: field to add
        :return:
        """
        if field.name == self.sub_type:
            field.default = self.sub_type_default
        if self.oid is not None and field.name.lower() == self.oid.lower():
            field.serial = True
        if field.is_geometry():
            self.geom = field
        else:
            self.fields.append(field)

    def list_fields(self, check_multi):
        """
        return a comma separated list with the name of the fields
        :param check_multi: if we have to check for MULTI geometry and then force the output
        :return:
        """
        f_list = ", ".join([f.name.lower() for f in self.get_valid_fields()])
        if self.geom is not None:
            if check_multi is True and self.geom.geom_info()["type"] in ("MULTILINESTRING", "MULTIPOLYGON"):
                f_list += ", ST_MULTI(geom) as geom"
            else:
                f_list += ", geom"
        return f_list
        
    def set_subtypes(self, subs):
        """
        set the subtype definition from the xml dom node
        :param subs: dome node containing the definition of the subtype for the feature class
        :return:
        """
        for sub in subs:
            name = sub.getElementsByTagName("SubtypeName")[0].childNodes[0].data
            code = sub.getElementsByTagName("SubtypeCode")[0].childNodes[0].data
            info = []
            f_info = sub.getElementsByTagName("FieldInfos")[0].getElementsByTagName("SubtypeFieldInfo")
            for f in f_info:
                f_name = f.getElementsByTagName("FieldName")[0].childNodes[0].data
                d_name = f.getElementsByTagName("DomainName")[0].childNodes[0].data
                info.append({
                    "field": f_name,
                    "domain": d_name
                })
            self.subtypes.append({
                "name": name,
                "code": code,
                "info": info
            })
        
    def get_valid_fields(self):
        """
        return an array with just the valid fields
        :return:
        """
        v_fields = []
        for f in self.fields:
            if f.is_valid():
                v_fields.append(f)
        return v_fields
        
    def get_domain_fields(self):
        """
        returns an array with just the fields with associated domains
        :return:
        """
        v_fields = []
        for f in self.fields:
            if f.is_valid() and f.domain is not None:
                v_fields.append(f)
        return v_fields    
        
    def is_valid(self):
        """
        Returns if the feature class can be considered valid.
        A feature class is valid if it contains at least 1 field and 1 geometry field
        :return:
        """
        if len(self.fields) > 0 and self.geom is not None:
            return True
        return False

    def __str__(self):
        """
        Returns the string representation of the object as SQL statements
        :return:
        """
        table_name = self.schema.lower() + "." + self.name.lower()
        view_name = self.schema.lower() + ".v_" + self.name.lower()
        sql = "CREATE TABLE %s(\n   " % table_name
        sql += ",\n   ".join([str(f) for f in self.get_valid_fields()])
        if self.oid is not None:
            sql += ", "
            sql += "PRIMARY KEY(" + self.oid
            if self.sub_type is not None:
                sql += ", " + self.sub_type
            sql += ") "
        sql += "\n)"
        if self.sub_type is not None:
            sql += " PARTITION BY LIST(%s)" % (self.sub_type,)
        sql += ";\n"
        
        if self.geom is not None:
            info = self.geom.geom_info()
            sql += "SELECT AddGeometryColumn ('%s', '%s', 'geom', %s, '%s', %s);\n" % (
                self.schema.lower(), self.name.lower(), str(info["epsg"]), info["type"], str(info["dim"]))
        if self.sub_type is None:
            cont = 0
            for f in self.get_domain_fields():
                cont += 1
                sql += "ALTER TABLE %s.%s ADD CONSTRAINT %s_FK_%s FOREIGN KEY(%s) REFERENCES %s.%s(CODE);\n" % (
                    self.schema.lower(), self.name.lower(), self.name.lower(), str(cont),
                    f.domain, self.schema.lower(), f.domain.lower())
        else:
            for s in self.subtypes:
                cont = 0
                partition_name = table_name + "_" + s["code"]
                p_name = self.name.lower() + "_" + s["code"]
                sql += "CREATE TABLE %s PARTITION OF %s FOR VALUES IN (%s);\n" % (partition_name, table_name, s["code"])
                for f in s["info"]:
                    cont += 1
                    sql += "ALTER TABLE %s ADD CONSTRAINT %s_FK_%s FOREIGN KEY(%s) REFERENCES %s.%s(CODE);\n" % (
                        partition_name, p_name, str(cont), f["field"], self.schema.lower(), f["domain"])
        sql += "CREATE OR REPLACE VIEW %s AS SELECT * FROM %s;\n" % (view_name, table_name)
        sql += "DELETE FROM public.gt_pk_metadata " \
               "WHERE table_schema = '%s' AND table_name = '%s' " \
               "AND pk_column='objectid';\n" % (self.schema.lower(), "v_" + self.name.lower())
        sql += "INSERT INTO public.gt_pk_metadata(table_schema, table_name, pk_column) "
        sql += "VALUES('%s', '%s', 'objectid');\n" % (self.schema.lower(), "v_" + self.name.lower())
        return sql


class KhrisXMLFeatureClassesImporterAlgorithm(QgsProcessingAlgorithm):
    """
    Algorithm to define and import feature classes from geopackage and EXRI Xml Workspace definition into PostGIS
    """
    def initAlgorithm(self, config=None):
        """
        Initialize the algorithm.
        It accepts the following parameters (via QGIS processing):
        - XMLPATH: path to the Xml Workspace definition of the geodatabase (for the geopackage to import)
        - GPKGPATH: path to the geopakcge to import
        - DBNAME: name of the database as defined in QGIS PG connection (default is 'KRIHS')
        - SCHEMA: name of the destination schema (default is 'public')
        - DROPIFEXISTS: name of the destination schema (default is 'public')
        """
        self.addParameter(QgsProcessingParameterString('XMLPATH', 'XML Workspace Definition', multiLine=False, defaultValue=''))
        self.addParameter(QgsProcessingParameterString('GPKGPATH', 'GeoPackage', multiLine=False, defaultValue=''))
        self.addParameter(QgsProcessingParameterString('DBNAME', 'Pg Connection Name', multiLine=False, defaultValue='KRIHS'))
        self.addParameter(QgsProcessingParameterString('SCHEMA', 'Schema', multiLine=False, defaultValue='public'))
        self.addParameter(QgsProcessingParameterBoolean('DROPIFEXISTS', 'Drop if exists', optional=True, defaultValue=True))

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

    def getDatasetDef(self, data_element):
        """
        Return the dataset definition from the dataset dom node
        :param data_element: dom node representing the dataset
        :return:
        """
        type = data_element.getElementsByTagName(TAG_DE_TYPE)[0].childNodes[0].data
        subtypes = data_element.getElementsByTagName(TAG_DE_SUBTYPE)
        subtype = None
        subtype_def = None
        subs = []
        if len(subtypes) > 0:
            subtype = data_element.getElementsByTagName(TAG_DE_SUBTYPE)[0].childNodes[0].data
            subtype_def = data_element.getElementsByTagName(TAG_DE_SUBTYPE_DEF)[0].childNodes[0].data
            subs = data_element.getElementsByTagName(TAG_DE_SUBTYPES)[0].getElementsByTagName(TAG_DE_SUBTYPES_SUBTYPE)
        
        if type == "esriDTFeatureClass":
            name = data_element.getElementsByTagName(TAG_DE_NAME)[0].childNodes[0].data
            oid = None
            has_oid = data_element.getElementsByTagName("HasOID")[0].childNodes[0].data
            if has_oid == "true":
                oid = data_element.getElementsByTagName("OIDFieldName")[0].childNodes[0].data
            feature_class = FeatureClass(name, oid, subtype, subtype_def, self.pg_schema)
            feature_class.set_subtypes(subs)
            fields = data_element.getElementsByTagName(TAG_DE_FIELDS)[0]
            fields_array = fields.getElementsByTagName(TAG_DE_FIELDS_ARR)[0]
            field_list = fields_array.getElementsByTagName(TAG_DE_FIELD)
            for field in field_list:
                fld = Field()
                fld.name = field.getElementsByTagName(TAG_DE_FIELD_NAME)[0].childNodes[0].data
                fld.type = field.getElementsByTagName(TAG_DE_FIELD_TYPE)[0].childNodes[0].data
                fld.isnull = field.getElementsByTagName(TAG_DE_FIELD_ISNULL)[0].childNodes[0].data
                fld.length = int(field.getElementsByTagName(TAG_DE_FIELD_LENGTH)[0].childNodes[0].data)
                fld.precision = int(field.getElementsByTagName(TAG_DE_FIELD_PRECISION)[0].childNodes[0].data)
                fld.scale = int(field.getElementsByTagName(TAG_DE_FIELD_SCALE)[0].childNodes[0].data)
                f_domain = field.getElementsByTagName(TAG_DE_FIELD_DOMAIN)
                domain_name = None
                if len(f_domain):
                    f_domain = f_domain[0]
                    domain_name = f_domain.getElementsByTagName(TAG_DE_FIELD_DOMAIN_NAME)[0].childNodes[0].data
                fld.domain = domain_name
                if fld.is_geometry():
                    fld.geom_def = field.getElementsByTagName(TAG_DE_GEOM_DEF)[0]
                
                feature_class.add_field(fld)
            sql = ""
            if self.pg_drop_before:
                sql += "DROP TABLE IF EXISTS %s.%s CASCADE;\n" % (self.pg_schema, name) 
                sql += "DROP TABLE IF EXISTS %s.%s_tmp CASCADE;\n" % (self.pg_schema, name) 
            sql += str(feature_class)
            return [name, sql, feature_class.list_fields(False), feature_class.list_fields(True), feature_class.geom.geom_info()["gtype"]] 
        else:
            return None

    def get_gpkg_vector_layer(self, name):
        """
        Return a QgsVectorLayer by name
        """
        layer = None
        try:
            gpkg_layer_name = self.gpkg_path + "|layername=" + name
            vlayer = QgsVectorLayer(gpkg_layer_name, name, "ogr")
            if vlayer.isValid():
                layer = vlayer
        except Exception as e:
            print(e)
        return layer

    def pk_metadata_ddl(self):
        """
        Return the SQL definition for the PK Metadata table (to use in GeoServer)
        :return:
        """
        sql = "CREATE TABLE if not exists public.gt_pk_metadata (\n"
        sql += "   table_schema VARCHAR(32) NOT NULL,\n"
        sql += "   table_name VARCHAR(32) NOT NULL,\n"
        sql += "   pk_column VARCHAR(32) NOT NULL,\n"
        sql += "   pk_column_idx INTEGER,\n"
        sql += "   pk_policy VARCHAR(32),\n"
        sql += "   pk_sequence VARCHAR(64),\n"
        sql += "   unique(table_schema, table_name, pk_column),\n"
        sql += "   check(pk_policy in ('sequence', 'assigned', 'autogenerated'))"
        sql += ");\n"
        return sql

    def create_pk_metadata_table(self, context, feedback):
        sql = self.pk_metadata_ddl()
        try:
            alg_params = {
                'DATABASE': self.pg_conn_name,
                'SQL': sql
            }
            feedback.pushInfo("   processing => qgis:postgisexecutesql")
            processing.run('qgis:postgisexecutesql',
                           alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        except Exception as e:
            feedback.reportError("Error creating table definition: \n" + sql + ": " + str(e), False)

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
        self.gpkg_path = parameters["GPKGPATH"]
        if not self.xml_path.lower().endswith(".xml"):
            feedback = QgsProcessingMultiStepFeedback(0, model_feedback)
            feedback.reportError("XML Workspace Definition is not an XML file!", True)
            return {}
        if not self.gpkg_path.lower().endswith(".gpkg"):
            feedback = QgsProcessingMultiStepFeedback(0, model_feedback)
            feedback.reportError("GeoPackage is not an GPKG file!", True)
            return {}    
        self.pg_conn_name = parameters["DBNAME"]
        self.pg_schema = parameters["SCHEMA"]
        self.pg_drop_before = parameters["DROPIFEXISTS"]
        dataset_list = self.getDatasets()
        feedback = QgsProcessingMultiStepFeedback(2+len(dataset_list), model_feedback)
        step = 0
        self.create_pk_metadata_table(context, feedback)
        step = 1
        for dataset in dataset_list:
            step += 1
            definition = self.getDatasetDef(dataset)
            if definition is not None:
                try:
                    in_layer = self.get_gpkg_vector_layer(definition[0])
                    if in_layer is not None:
                        feedback.pushInfo("Feature Class: " + definition[0])
                        try:
                            alg_params = {
                                'DATABASE': self.pg_conn_name,
                                'SQL': definition[1]
                            }
                            feedback.pushInfo("   processing (A) => qgis:postgisexecutesql")
                            processing.run('qgis:postgisexecutesql',
                                           alg_params, context=context, feedback=feedback, is_child_algorithm=True)
                        except Exception as e1:
                            feedback.reportError("Error creating table definition: \n" + definition[1] + ": " + str(e1), False)
                            break
                        
                        try:
                            # Esporta in PostgreSQL (connessioni disponibili)
                            alg_params = {
                                'ADDFIELDS': False,
                                'APPEND': False,
                                'A_SRS': None,
                                'CLIP': False,
                                'DATABASE': self.pg_conn_name,
                                'DIM': 0,
                                'GEOCOLUMN': 'geom',
                                'GT': '',
                                'GTYPE': definition[4],
                                'INDEX': False,
                                'INPUT': self.get_gpkg_vector_layer(definition[0]),
                                'LAUNDER': False,
                                'OPTIONS': '',
                                'OVERWRITE': True,
                                'PK': '',
                                'PRECISION': True,
                                'PRIMARY_KEY': '',
                                'PROMOTETOMULTI': True,
                                'SCHEMA': self.pg_schema,
                                'SEGMENTIZE': '',
                                'SHAPE_ENCODING': '',
                                'SIMPLIFY': '',
                                'SKIPFAILURES': False,
                                'SPAT': None,
                                'S_SRS': None,
                                'TABLE': definition[0].lower() + '_tmp',
                                'T_SRS': None,
                                'WHERE': ''
                            }
                            feedback.pushInfo("   processing (B) => qgis:importvectorintopostgisdatabaseavailableconnections")
                            processing.run('gdal:importvectorintopostgisdatabaseavailableconnections', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
                        except Exception as e2:
                            feedback.reportError("Error importing data: \n" + definition[0] + ": " + str(e2), False)
                            break        
                
                        try:
                            #Copy from TMP to FINAL table
                            sql_copy = "INSERT INTO %s.%s(%s) SELECT %s FROM %s.%s_tmp" % (self.pg_schema, definition[0], definition[2], definition[3], self.pg_schema, definition[0]) + ";"
                            sql_drop = "DROP TABLE %s.%s_tmp" % (self.pg_schema, definition[0]) + ";"
                            alg_params = {
                                'DATABASE': self.pg_conn_name,
                                'SQL': sql_copy + sql_drop
                            }
                            feedback.pushInfo("   processing (C) => qgis:postgisexecutesql")
                            processing.run('qgis:postgisexecutesql', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
                        except Exception as e3:
                            feedback.reportError("Error moving data: \n" + sql_copy + sql_drop + ": " + str(e3), False)
                            break
                except Exception as e:
                    feedback.reportError("Error importing domain " + definition[1] + ": " + str(e), False)
            feedback.setCurrentStep(step)
        results = {}
        outputs = {}
        return results

    def name(self):
        """
        Name of the algorithm
        :return:
        """
        return 'KhrisXMLFeatureClassesImporterAlgorithm'

    def displayName(self):
        """
        Name to display for the algorithm in QGIS
        :return:
        """
        return 'XML Feature Classes Importer'

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
        return KhrisXMLFeatureClassesImporterAlgorithm()
