from __future__ import absolute_import, division, print_function, unicode_literals
import logging.config
import config_logger

logging.config.dictConfig(config_logger.config)
logging.raiseExceptions = False
logger = logging.getLogger('main')
logger.info("Logging Started")


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

class Documents:
    def __init__(self, settings):
        self.__settings = settings

    @property
    def items_to_publish(self):
        return [Doc(self.__settings,"")]

    @property
    def items_to_unpublish(self):
        return []


class Doc:
    def __init__(self, config, path):
        self.__config = config
        self.path = path

    @property
    def name(self):
        return "Unknown"

    @property
    def is_publishable(self):
        return True

    @property
    def issues(self):
        return None

    def publish(self):
        pass

    def unpublish(self):
        pass


def get_configuration_settings():
    try:
        import config
    except ImportError as err:
        logger.warning("Unable to load the config file: %s", err)

        class Config:
            def __init__(self):
                pass
        config = Config()

    # Ensure defaults exist to avoid AttributeErrors below
    config.root_directory = getattr(config, 'root_directory', None)

    import argparse
    parser = argparse.ArgumentParser(description='Syncs a set of ArcGIS Web Services with source documents')

    if config.root_directory is None:
        parser.add_argument('root_directory', metavar='PATH',  help='The directory of documents to publish.')
    else:
        parser.add_argument('root_directory', nargs='?', metavar='PATH', default=config.root_directory,
                            help=('The directory of documents to publish. '
                                  'The default is {0}').format(config.root_directory))
    parser.add_argument('-v', '--verbose', action='store_true', help='Show informational messages.')
    parser.add_argument('--debug', action='store_true', help='Show extensive debugging messages.')

    args = parser.parse_args()

    if args.verbose:
        logger.parent.handlers[0].setLevel(logging.INFO)
        logger.info("Started logging at INFO level")
    if args.debug:
        logger.parent.handlers[0].setLevel(logging.DEBUG)
        logger.debug("Started logging at DEBUG level")
        logger.debug("Command line argument %s", args)

    return args


def main():
    settings = get_configuration_settings()
    documents = Documents(settings)
    for doc in documents.items_to_publish:
        if doc.is_publishable:
            try:
                doc.publish()
            except PublishException as ex:
                logger.error("Unable to publish %s because %s", doc.name, ex.message)
        else:
            logger.warn("Unable to publish %s because %s", doc.name, doc.issues)
    for doc in documents.items_to_unpublish:
        try:
            doc.unpublish()
        except PublishException as ex:
            logger.error("Unable to remove service for %s because %s", doc.name, ex)


if __name__ == '__main__':
    main()
