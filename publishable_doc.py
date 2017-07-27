from __future__ import absolute_import, division, print_function, unicode_literals
import os.path
import logging

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class PublishException(Exception):
    """Raise when unable to Make a change on the server"""


class Doc(object):
    def __init__(self, path, folder=None, server=None, config=None):
        logger.debug("Doc.__init__(path=%s, folder=%s, server=%s, config=%s",
                     path, folder, server, config)
        self.__config = config
        # FIXME: Check that folder and path are valid, before we generate errors
        self.folder = folder
        self.path = path
        base, ext = os.path.splitext(path)
        self.__basename = os.path.basename(base)
        self.__ext = ext
        self.__draft_file_name = base + '.sddraft'
        self.__sd_file_name = base + '.sd'
        self.__sd_file_is_ready = False
        self.__service_name = self.__sanitize_service_name(self.__basename)
        self.__folder_name = self.__sanitize_service_name(folder)
        self.__service_copy_data_to_server = False
        self.__service_server_type = None
        self.__service_connection_file_path = None
        if server is not None:
            self.server = server
        else:
            try:
                self.server = self.__config.server
            except AttributeError:
                self.server = None
        self.__service_summary = None  # or string
        self.__service_tags = None  # or string with comma separated tags

    @property
    def name(self):
        if self.folder is None:
            return self.__basename
        else:
            return self.folder + '/' + self.__basename

    @property
    def service_path(self):
        if self.__folder_name is None:
            return self.__service_name
        else:
            return self.__folder_name + '/' + self.__service_name

    @property
    def server(self):
        if self.__service_server_type == 'MY_HOSTED_SERVICES':
            return self.__service_server_type
        else:
            return self.__service_connection_file_path

    @server.setter
    def server(self, new_value):
        """Set the server connection type/details

        Must be 'MY_HOSTED_SERVICES', or a valid file path.
        Any other value will default to 'MY_HOSTED_SERVICES'"""

        hosted = 'MY_HOSTED_SERVICES'
        conn_file = 'FROM_CONNECTION_FILE'
        # default
        self.__service_server_type = hosted
        self.__service_connection_file_path = None

        if new_value is None or new_value.lower() == hosted.lower():
            logger.debug('Setting document %s service_server_type to %s and service_connection_file_path to %s',
                         self.name, self.__service_server_type, self.__service_connection_file_path)
            return

        try:
            if os.path.exists(new_value):
                self.__service_server_type = conn_file
                self.__service_connection_file_path = new_value
            else:
                logger.warn('Connection file (%s) not found. Using default.', new_value)
        except TypeError:
            logger.warn("Server must be None, '%s', or a file path.  Got %s. Using default.", hosted, new_value)

        logger.debug('Setting document %s service_server_type to %s and service_connection_file_path to %s',
                     self.name, self.__service_server_type, self.__service_connection_file_path)

    @property
    def is_publishable(self):
        return True

    @property
    def issues(self):
        return None

    @property
    def sd_file(self):
        if self.__sd_file_is_ready:
            return self.__sd_file_name
        else:
            return None

    def publish(self):
        pass

    def unpublish(self):
        pass

    @staticmethod
    def __sanitize_service_name(name, replacement='_'):
        """Replace all non alphanumeric characters with replacement

        The name can only contain alphanumeric characters and underscores.
        No spaces or special characters are allowed.
        The name cannot be more than 120 characters in length.
        http://desktop.arcgis.com/en/arcmap/latest/analyze/arcpy-mapping/createmapsddraft.htm"""

        if name is None:
            return None
        clean_chars = [c if c.isalnum() else replacement for c in name]
        return ''.join(clean_chars)[:120]

    def __is_image_service(self):
        # TODO: Implement
        return self.path is None

    def __create_draft_service_definition(self):
        """Create a service definition draft from a mxd/lyr

        ref: http://desktop.arcgis.com/en/arcmap/latest/analyze/arcpy-functions/createimagesddraft.htm
        ref: http://desktop.arcgis.com/en/arcmap/latest/analyze/arcpy-mapping/createmapsddraft.htm
        """

        import arcpy

        # FIXME: check inputs
        if self.__is_image_service:
            create_sddraft = arcpy.CreateImageSDDraft
        else:
            create_sddraft = arcpy.mapping.CreateMapSDDraft

        try:
            create_sddraft(self.path, self.__draft_file_name, self.__service_name,
                           self.__service_server_type, self.__service_connection_file_path,
                           self.__service_copy_data_to_server, self.__folder_name,
                           self.__service_summary, self.__service_tags)
        except Exception as ex:
            raise PublishException(ex.message)

        # FIXME: Make a replacement service if service exists

    def __create_service_definition(self):
        """Create a Service Definition from a Draft

        both are file paths, the first exists, the second does not"""

        # FIXME: check inputs

        import arcpy

        arcpy.StageService_server(self.__draft_file_name, self.__sd_file_name)

        # FIXME: check for success

    def create_replacement_service_draft(self):
        """Modify the service definition draft to overwrite the existing service

        The existing draft file is overwritten.
        Need to check if this is required before calling.
        """
        import xml.dom.minidom as dom

        new_type = 'esriServiceDefinitionType_Replacement'
        file_name = self.__draft_file_name

        xdoc = dom.parse(file_name)
        descriptions = xdoc.getElementsByTagName('Type')
        for desc in descriptions:
            if desc.parentNode.tagName == 'SVCManifest':
                if desc.hasChildNodes():
                    desc.firstChild.data = new_type

        # FIXME: provide python2 and python3 varieties
        with open(file_name, u'w') as f:
            xdoc.writexml(f)

    def __publish_service(self):
        """Publish Service Definition

        Uploads and publishes a GIS service to a specified GIS server based on a staged service definition (.sd) file.
        http://desktop.arcgis.com/en/arcmap/latest/tools/server-toolbox/upload-service-definition.htm

        server can be one of the following
        A name of a server connection in ArcCatalog; i.e. server = r'GIS Servers/arcgis on my_server (publisher)'
        A full path to an ArcGIS Server connection file (*.ags) created in ArcCatalog;
          i.e. server = r'C:\path\to\my\connection.ags'
        A relative path (relative to the cwd of the process running the script) to an ArcGIS Server connection
          file (*.ags) created in ArcCatalog
        'My Hosted Services' to publish to AGOL or Portal (you must be signed in to one or the other for this to work.)

        sd_file (A service definition (.sd) contains all the information needed to publish a GIS service) can be
        A full path to an sd file
        A relative path (relative to the cwd of the process running the script) to an sd file
        A relative path (relative to the arcpy.env.workspace setting) to an sd file

        This will publish the sd_file to the server with the following defaults
          (can be overridden with additional parameters)
        the service will be created with the folder/name as specified in the sd_file
        the service will be assigned to the default cluster
        service will be started after publishing
        AGOL/Portal services will be shared per the settings in the sd_file
        """

        import arcpy

        sd_file = self.sd_file
        if sd_file is None:
            PublishException("Service Definition (*.sd) file is not ready to publish")

        asg_file = self.__service_connection_file_path
        if asg_file is None:
            PublishException("No Server Connection File (*.asg) file provided")
        if not arcpy.Exists(asg_file):
            PublishException("Server Connection File ({0}) file not found".format(asg_file))

        try:
            logger.debug("Begin arcpy.UploadServiceDefinition_server(%s, %s)", sd_file, asg_file)
            arcpy.UploadServiceDefinition_server(sd_file, asg_file)
            logger.debug("arcpy.UploadServiceDefinition_server() complete")
        except Exception as ex:
            raise PublishException(ex.message)


# Testing
def test_path_folder_input():
    doc = Doc(r'.\test_data\test.mxd')
    print('Local name:', doc.name, '|    Service path:', doc.service_path)
    assert doc.name == 'test' and doc.service_path == 'test'

    doc = Doc(r'.\test_data\test.mxd', folder=None)
    print('Local name:', doc.name, '|    Service path:', doc.service_path)
    assert doc.name == 'test' and doc.service_path == 'test'

    doc = Doc(r'.\test_data\folder\test.mxd', folder='folder')
    print('Local name:', doc.name, '|    Service path:', doc.service_path)
    assert doc.name == 'folder/test' and doc.service_path == 'folder/test'

    doc = Doc(r'.\test_data\my weird name!.mxd', folder='%funky folder%')
    print('Local name:', doc.name, '|    Service path:', doc.service_path)
    assert doc.name == '%funky folder%/my weird name!' and doc.service_path == '_funky_folder_/my_weird_name_'


def test_server_input():
    class TestConfig(object):
        def __init__(self):
            pass
    config = TestConfig()
    print("test no config object (no warning; use default)")
    doc = Doc(r'.\test_data\test.mxd')
    print('    Server:', doc.server)
    assert doc.server == 'MY_HOSTED_SERVICES'

    print("test no server attribute on config (no warning; use default)")
    doc = Doc(r'.\test_data\test.mxd', config=config)
    print('    Server:', doc.server)
    assert doc.server == 'MY_HOSTED_SERVICES'

    print("test config.server is None (no warning; use default)")
    setattr(config, 'server', None)
    doc = Doc(r'.\test_data\test.mxd', config=config)
    print('    Server:', doc.server)
    assert doc.server == 'MY_HOSTED_SERVICES'

    print("test config.server is int (should warn and use default)")
    config.server = 1
    doc = Doc(r'.\test_data\test.mxd', config=config)
    print('    Server:', doc.server)
    assert doc.server == 'MY_HOSTED_SERVICES'

    print("test config.server is junk text (should warn and use default)")
    config.server = 'junk'
    doc = Doc(r'.\test_data\test.mxd', config=config)
    print('    Server:', doc.server)
    assert doc.server == 'MY_HOSTED_SERVICES'

    print("test config.server is file (no warning; use file)")
    config.server = r'.\test_data\test.ags'
    doc = Doc(r'.\test_data\test.mxd', config=config)
    print('    Server:', doc.server)
    assert doc.server == r'.\test_data\test.ags'

    print("test config.server is MY_HOSTED_SERVICES (no warning; use setting)")
    config.server = 'MY_HOSTED_SERVICES'
    doc = Doc(r'.\test_data\test.mxd', config=config)
    print('    Server:', doc.server)
    assert doc.server == 'MY_HOSTED_SERVICES'

    print("test service parameter is None (no warning; should use config)")
    config.server = r'.\test_data\test.ags'
    doc = Doc(r'.\test_data\test.mxd', server=None, config=config)
    print('    Server:', doc.server)
    assert doc.server == r'.\test_data\test.ags'

    print("test service parameter is int (should warn and use default)")
    doc = Doc(r'.\test_data\test.mxd', server=1, config=config)
    print('    Server:', doc.server)
    assert doc.server == 'MY_HOSTED_SERVICES'

    print("test service parameter is junk text (should warn and use default)")
    doc = Doc(r'.\test_data\test.mxd', server='junk', config=config)
    print('    Server:', doc.server)
    assert doc.server == 'MY_HOSTED_SERVICES'

    print("test service parameter is is file (no warning; use file)")
    doc = Doc(r'.\test_data\test.mxd', server=r'.\test_data\test2.ags', config=config)
    print('    Server:', doc.server)
    assert doc.server == r'.\test_data\test2.ags'

    print("test service parameter is MY_HOSTED_SERVICES (no warning; use setting")
    doc = Doc(r'.\test_data\test.mxd', server='MY_HOSTED_SERVICES', config=config)
    print('    Server:', doc.server)
    assert doc.server == 'MY_HOSTED_SERVICES'


if __name__ == '__main__':
    logger.addHandler(logging.StreamHandler())
    # logger.setLevel(logging.DEBUG)
    test_path_folder_input()
    test_server_input()
