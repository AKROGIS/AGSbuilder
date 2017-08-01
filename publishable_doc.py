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
        self.__basename = None
        self.__ext = None
        self.__draft_file_name = None
        self.__sd_file_name = None
        self.__is_image_service = False
        self.__path = None
        self.path = path
        self.__folder = None
        self.folder = folder
        self.__service_name = self.__sanitize_service_name(self.__basename)
        self.__service_folder_name = self.__sanitize_service_name(self.folder)
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
        self.__have_draft = False
        self.__draft_analysis_result = None
        self.__have_service_definition = False

    @property
    def path(self):
        return self.__path

    @path.setter
    def path(self, new_value):
        """Make sure new_value is text or set to None"""
        try:
            # FIXME: if this is an image service then it is a dataset a fgdb (which isn't a real file)
            # TODO: set self.__is_image_service here
            if os.path.exists(new_value):
                self.__path = new_value
                base, ext = os.path.splitext(new_value)
                self.__basename = os.path.basename(base)
                self.__ext = ext
                # TODO: Allow draft and sd to be created in a new location from settings (path may be read only)
                # TODO: This will not work for image services
                self.__draft_file_name = base + '.sddraft'
                self.__sd_file_name = base + '.sd'
            else:
                logger.warn('Path (%s) Not found. This is an invalid document.', new_value)
        except TypeError:
            logger.warn("Path must be text.  Got %s. This is an invalid document.", type(new_value))

    @property
    def folder(self):
        return self.__folder

    @folder.setter
    def folder(self, new_value):
        """Make sure new_value is text or set to None"""
        if new_value is None:
            self.__folder = None
            return
        try:
            _ = new_value.isalnum()
            self.__folder = new_value
        except AttributeError:
            logger.warn("Folder must be None, or text.  Got %s. Using None.", type(new_value))
            self.__folder = None

    @property
    def name(self):
        if self.folder is not None and self.__basename is not None:
            return self.folder + '/' + self.__basename
        return self.__basename

    @property
    def service_path(self):
        if self.__service_folder_name is not None and self.__service_name is not None:
            return self.__service_folder_name + '/' + self.__service_name
        return self.__service_name

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

        # if you want to do a case insensitive compare, be careful, as new_value may not be text.
        if new_value is None or new_value == hosted:
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
        """
        Check if a source is ready to publish to the server.

        Returns True or False, should not throw any exceptions.
        May need to create a draft service definition to analyze the file.  Any exceptions will be swallowed.
        If there is an existing sd file newer than the source, then we are ready to publish, otherwise
        create a draft file (if necessary) and analyze.  If there are no errors in the analysis then it
        is ready to publish.

        :return: Bool
        """
        if not self.__is_image_service and os.path.exists(self.__sd_file_name):
            src_mtime = os.path.getmtime(self.path)
            dst_mtime = os.path.getmtime(self.__sd_file_name)
            if src_mtime < dst_mtime:
                logger.debug("Service definition is newer than source, ready to publish.")
                return True

        if not self.__draft_analysis_result:
            try:
                self.__analyze_draft_service_definition()
            except PublishException as ex:
                logger.warn("Unable to analyze the service: %s", ex.message)
                return False
        if not self.__draft_analysis_result:
            logger.warn("Unable to analyze service definition draft, NOT ready to publish.")
            return False
        if 0 < len(self.__draft_analysis_result['errors']):
            logger.debug("Service definition draft has errors, NOT ready to publish.")
            return False
        return True

    @property
    def issues(self):
        if not self.__draft_analysis_result:
            try:
                self.__analyze_draft_service_definition()
            except PublishException as ex:
                logger.warn("Unable to analyze the service: %s", ex.message)
                return False
        if not self.__draft_analysis_result:
            return False
        if 0 == len(self.__draft_analysis_result['errors']):
            return None
        return self.__draft_analysis_result['errors']

    def publish(self):
        # TODO: Implement
        pass

    def unpublish(self):
        # TODO: Implement
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

    def __create_draft_service_definition(self, force=False):
        """Create a service definition draft from a mxd/lyr

        Note: a *.sddraft file is deleted once it is used to create a *.sd file

        ref: http://desktop.arcgis.com/en/arcmap/latest/analyze/arcpy-functions/createimagesddraft.htm
        ref: http://desktop.arcgis.com/en/arcmap/latest/analyze/arcpy-mapping/createmapsddraft.htm
        """
        logger.debug("Creating Draft Service Definition from %s", self.path)

        if self.path is None:
            raise PublishException('This document cannot be published.  There is no path to the source.')

        if not os.path.exists(self.path):
            raise PublishException('This document cannot be published.  The source file is missing.')

        if os.path.exists(self.__draft_file_name):
            if force:
                self.__delete_file(self.__draft_file_name)
            else:
                src_mtime = os.path.getmtime(self.path)
                dst_mtime = os.path.getmtime(self.__draft_file_name)
                if src_mtime < dst_mtime:
                    logger.info("sddraft is newer than source document, skipping.")
                    self.__have_draft = True
                    return
                else:
                    self.__delete_file(self.__draft_file_name)

        import arcpy

        source = self.path
        if self.__is_image_service:
            create_sddraft = arcpy.CreateImageSDDraft
        else:
            create_sddraft = arcpy.mapping.CreateMapSDDraft
            try:
                source = arcpy.mapping.MapDocument(self.path)
            except Exception as ex:
                PublishException(ex.message)

        try:
            r = create_sddraft(source, self.__draft_file_name, self.__service_name,
                               self.__service_server_type, self.__service_connection_file_path,
                               self.__service_copy_data_to_server, self.__service_folder_name,
                               self.__service_summary, self.__service_tags)
            self.__draft_analysis_result = r
            self.__have_draft = True
        except Exception as ex:
            raise PublishException(ex.message)

        # TODO: Make a replacement service if service exists

    def __analyze_draft_service_definition(self):
        """Analyze a Service Definition Draft (.sddraft) files for readiness to publish

        http://desktop.arcgis.com/en/arcmap/latest/analyze/arcpy-mapping/analyzeforsd.htm
        """
        if self.__draft_analysis_result is not None:
            return

        if not self.__have_draft:
            self.__create_draft_service_definition()
        if not self.__have_draft:
            logger.error('Unable to get a draft service definition to analyze')
            return
        import arcpy
        try:
            self.__draft_analysis_result = arcpy.mapping.AnalyzeForSD(r"C:\Project\Counties.sddraft")
        except Exception as ex:
            PublishException('Unable to analyze draft service definition: %s', ex.message)

    def __create_service_definition(self, force=False):
        """Converts a service definition draft (.sddraft) into a service definition

        Once staged, the input draft service definition is deleted.
        Calling is_publishable will check for an existing *.sd file that is newer than source

        http://desktop.arcgis.com/en/arcmap/latest/tools/server-toolbox/stage-service.htm
        """
        if force:
            self.__delete_file(self.__sd_file_name)

        if not self.is_publishable:
            PublishException("Service Definition Draft has issues and is not ready to publish")

        try:
            import arcpy
            arcpy.StageService_server(self.__draft_file_name, self.__sd_file_name)
            self.__have_service_definition = True
        except Exception as ex:
            PublishException('Unable to analyze draft service definition: %s', ex.message)

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

        if not self.__have_service_definition:
            self.__create_service_definition()
        if not self.__have_service_definition:
            PublishException("Service Definition (*.sd) file is not ready to publish")

        if self.__service_connection_file_path is None:
            # conn = ' '.join([word.capitalize() for word in self.__service_server_type.split('_')])
            conn = 'My Hosted Services'
        else:
            conn = self.__service_connection_file_path

        try:
            import arcpy
            logger.debug("Begin arcpy.UploadServiceDefinition_server(%s, %s)", self.__sd_file_name, conn)
            # TODO: Support the other options
            arcpy.UploadServiceDefinition_server(self.__sd_file_name, conn)
            logger.debug("arcpy.UploadServiceDefinition_server() complete")
        except Exception as ex:
            raise PublishException(ex.message)

    @staticmethod
    def __delete_file(path):
        try:
            logger.debug("deleting %s", path)
            os.remove(path)
        except Exception:
            raise PublishException('Unable to delete {0}'.format(path))



# Testing
def test_path_folder_input():

    # No need to test no path
    # IDE will give a warning about missing parameter, and we will crash right away (programming error)

    print("test path is None; Issues Warning")
    doc = Doc(None)
    print('Local name:', doc.name, '|    Service path:', doc.service_path)
    assert doc.name is None and doc.service_path is None

    print("test path is int; Issues Warning")
    doc = Doc(1)
    print('Local name:', doc.name, '|    Service path:', doc.service_path)
    assert doc.name is None and doc.service_path is None

    print("test path is junk text; Issues Warning")
    doc = Doc('junk')
    print('Local name:', doc.name, '|    Service path:', doc.service_path)
    assert doc.name is None and doc.service_path is None

    print("test path is valid file; no folder")
    doc = Doc(r'.\test_data\test.mxd')
    print('Local name:', doc.name, '|    Service path:', doc.service_path)
    assert doc.name == 'test' and doc.service_path == 'test'

    print("test path is valid file; folder is None")
    doc = Doc(r'.\test_data\test.mxd', folder=None)
    print('Local name:', doc.name, '|    Service path:', doc.service_path)
    assert doc.name == 'test' and doc.service_path == 'test'

    print("test path is valid file; folder is int; Issues Warning")
    doc = Doc(r'.\test_data\folder\test2.mxd', folder=1)
    print('Local name:', doc.name, '|    Service path:', doc.service_path)
    assert doc.name == 'test2' and doc.service_path == 'test2'

    print("test path is valid file; folder is text")
    doc = Doc(r'.\test_data\folder\test2.mxd', folder='folder')
    print('Local name:', doc.name, '|    Service path:', doc.service_path)
    assert doc.name == 'folder/test2' and doc.service_path == 'folder/test2'

    print("test path is invalid file; folder is text; Issues Warning")
    doc = Doc(r'.\test_data\folder\test.mxd', folder='folder')
    print('Local name:', doc.name, '|    Service path:', doc.service_path)
    assert doc.name is None and doc.service_path is None

    print("test path is valid file; folder is text (both have special characters)")
    doc = Doc(r'.\test_data\my weird name!.mxd', folder='%funky folder%')
    print('Local name:', doc.name, '|    Service path:', doc.service_path)
    assert doc.name == '%funky folder%/my weird name!' and doc.service_path == '_funky_folder_/my_weird_name_'

    print("test path is valid file; folder is text (both have special characters)")
    doc = Doc(r'.\test_data\%funky folder%\test3.mxd', folder='%funky folder%')
    print('Local name:', doc.name, '|    Service path:', doc.service_path)
    assert doc.name == '%funky folder%/test3' and doc.service_path == '_funky_folder_/test3'


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
