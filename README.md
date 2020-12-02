# C198-KRIHS

## Description
This project contains models and tools for QGIS (v3.12.2) to import layers and tables into PostGIS from a geopackage 
and the ESRI xml Workspace definition.

### Dependencies
- geoserver-restconfig

#### Install geoserver-restconfig
The publisher module requires to install the python library geoserver-restconfig using the Python interpreter of QGIS:
From the Python path of QGIS execute:
> python.exe -m pip install geoserver-config

If you have problem to connect with the pypi repositories it is possible to download manually whl files and then install it:
gisdata 0.5.4
geoserver-restconfig
The installation process is the same. But instead of using name of the libraries use the filename of download libraries:
> python.exe -m pip install gisdata-0.5.4.tar.gz
> python.exe -m pip install geoserver_restconfig-2.0.4.8-py3-none-any.whl

## Data

### gpkg-specifications.xsd 
This is the schema defining the ESRI xml Workspace of a geodatabase

### CONP.xml
Workspace definition of the CONP geodatabase

### UNMAP.xml
Workspace definition of the UNMAP geodatabase

## Scripts
This folder contains the python scripts used to:
- create domains tables and load their data
- create feature classes with subtypes (via declarative partitioning in PG) and load their features
- publish feature to GeoServer via ReST Admin Interface
Copy these 3 python scripts in the processing scripts folder of QGIS

## Models
This folder contains the model (*.model3) to use to create database structure for:
- domains table
- feature class (with subtypes)
Copy the .model3 file in the processing models folder of QGIS
