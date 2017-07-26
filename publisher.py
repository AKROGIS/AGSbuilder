# input:
#  1) A root folder with a set of mxd/lyr files optionally in folders (1 deep)
#  2) Table (csv, fgdb, sql, ...) of publishing properties for each item in (1)
#  3) Cached copy of (2) from last run to identify changes
#  4) Cached set of service definition files (*.sd) created from (1) & (2)
#  5) Connection to server to check for existing services
#
# operation:
#  read (3) (it will be empty on the first run)
#  read (2) fail if it is missing
#  read (1)
#  delete services:
#    if there is an item in (3) that is not in (1) check if it is in (5) if so, delete it
#  for each item in (1):
#    if no matching record in (2) use default set of properties
#    if it is marked as 'skip' in (2)
#    if modified date of item is newer than (4)[item] or (2)[item] is different than 3[item]
#       create new *.sd
#    


import arcpy


# Create a service definition draft from a mxd/lyr
# ========================================

arcpy.mapping.CreateMapSDDraft()
arcpy.CreateImageSDDraft()


# If necessary, create an "overwrite" Service Definition Draft
# ========================================
import xml.dom.minidom as dom

inServiceDefinitionDraft = r"C;\pathto\myMapService.sddraft"
outServiceDefinitionDraft = r"C;\pathto\myMapService_1.sddraft"
newType = 'esriServiceDefinitionType_Replacement'

xml = inServiceDefinitionDraft
doc = dom.parse(xml)
descriptions = doc.getElementsByTagName('Type')
for desc in descriptions:
    if desc.parentNode.tagName == 'SVCManifest':
        if desc.hasChildNodes():
            desc.firstChild.data = newType
    
with open(outServiceDefinitionDraft, 'w') as f:     
    doc.writexml(f)


# Create a Service Definition from a Draft
# ========================================
# both are file paths, the first exists, the second does not
arcpy.StageService_server(inServiceDefinitionDraft, outServiceDefinitionDraft)


# Publish Service Definition
# ========================================
# Uploads and publishes a GIS service to a specified GIS server based on a staged service definition (.sd) file.
# http://desktop.arcgis.com/en/arcmap/latest/tools/server-toolbox/upload-service-definition.htm

# server can be one of the following
# A name of a server connection in ArcCatalog; i.e. server = r'GIS Servers/arcgis on inpakrovmgis_6080 (publisher)'
# A full path to an ArcGIS Server connection file (*.ags) created in ArcCatalog;
#   i.e. server = r'C:\path\to\my\connection.ags'
# A relative path (relative to the cwd of the process running the script) to an ArcGIS Server connection
#   file (*.ags) created in ArcCatalog
# 'My Hosted Services' to publish to AGOL or Portal (you must be signed in to one or the other for this to work.)

# sd_file (A service definition (.sd) contains all the information needed to publish a GIS service) can be 
# A full path to an sd file
# A relative path (relative to the cwd of the process running the script) to an sd file
# A relative path (relative to the arcpy.env.workspace setting) to an sd file

# This will publish the sd_file to the server with the following defaults (can be overridden with additional parameters) 
# the service will be created with the folder/name as specified in the sd_file
# the service will be assigned to the default cluster
# service will be started after publishing
# AGOL/Portal services will be shared per the settings in the sd_file

try:
    arcpy.UploadServiceDefinition_server(sd_file, server)        
except Exception, e:
    print e.message

