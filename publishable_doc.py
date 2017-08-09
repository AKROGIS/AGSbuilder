from __future__ import absolute_import, division, print_function, unicode_literals
import os.path
import logging
import requests
from io import open  # for python2/3 compatibility

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class PublishException(Exception):
    """Raise when unable to Make a change on the server"""


class Doc(object):
    def __init__(self, path, folder=None, server=None, server_url=None, config=None):
        logger.debug("Doc.__init__(path=%s, folder=%s, server=%s, server_url=%s, config=%s",
                     path, folder, server, server_url, config)
        self.server_url = server_url
        self.__config = config
        self.__basename = None
        self.__ext = None
        self.__draft_file_name = None
        self.__sd_file_name = None
        self.__issues_file_name = None
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
        self.__have_new_service_definition = False
        self.__service_is_live = None

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
                self.__issues_file_name = base + '.issues.json'
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
        if not self.__is_image_service:
            if self.__file_exists_and_is_newer(self.__sd_file_name, self.path):
                logger.debug("Service definition is newer than source, ready to publish.")
                self.__have_service_definition = True
                return True

        # I need to create a sd file, so I need to check for/create a draft file
        if not self.__file_exists_and_is_newer(self.__draft_file_name, self.path):
            self.__create_draft_service_definition()

        # I may have a draft file, but it may not be publishable, make sure I have analysis results.
        if self.__draft_analysis_result is None:
            try:
                self.__analyze_draft_service_definition()
            except PublishException as ex:
                logger.warn("Unable to analyze the service: %s", ex.message)
                return False

        if self.__draft_analysis_result is None:
            logger.warn("Unable to analyze service definition draft, NOT ready to publish.")
            return False

        if 'errors' in self.__draft_analysis_result and 0 < len(self.__draft_analysis_result['errors']):
            logger.debug("Service definition draft has errors, NOT ready to publish.")
            return False
        return True

    @property
    def issues(self):
        """Provide a list of errors, warning and messages about publishing this document

        The issues are created when a draft file is created or re-analyzed.
        Since the draft file is deleted when a sd file is created, the analysis results are
        cached.  The cached copy is used if the sd file is newer than the map.
        If there is not cached copy, or the sd file is out of date, the draft file will be created or re-analyzed."""
        if self.__draft_analysis_result is None:
            self.__get_analysis_result_from_cache()

        if self.__draft_analysis_result is None:
            try:
                self.__analyze_draft_service_definition()
            except PublishException as ex:
                logger.warn("Unable to analyze the service: %s", ex.message)

        if self.__draft_analysis_result is None:
            return "Unable to get issues"

        return self.__stringify_analysis_results()

    def publish(self):
        self.__publish_service()

    def unpublish(self):
        """Stop and delete a service that is already published

        This requires Rest API URL, Admin credentials and the AGS Rest API
        The ags connection file cannot by used with arcpy to admin the server
        ref: http://resources.arcgis.com/en/help/rest/apiref/index.html
        """
        logger.debug("Stop and Remove %s", self.service_path)
        # TODO: Implement
        logger.warn("Unpublish not implemented.")

    @property
    def is_live(self):
        if self.__service_is_live is None:
            self.__service_is_live = self.__check_server_for_service()
        return self.__service_is_live

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

        if not force and self.__file_exists_and_is_newer(self.__draft_file_name, self.path):
            logger.info("sddraft is newer than source document, skipping create")
            self.__have_draft = True
            return

        if os.path.exists(self.__draft_file_name):
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
            logger.info("Begin arcpy.createSDDraft(%s)", self.path)
            r = create_sddraft(source, self.__draft_file_name, self.__service_name,
                               self.__service_server_type, self.__service_connection_file_path,
                               self.__service_copy_data_to_server, self.__service_folder_name,
                               self.__service_summary, self.__service_tags)
            logger.info("Done arcpy.createSDDraft()")
            self.__draft_analysis_result = r
            self.__have_draft = True
            self.__simplify_and_cache_analysis_results()
        except Exception as ex:
            raise PublishException(ex.message)

        if self.is_live:
            self.__create_replacement_service_draft()

    def __check_server_for_service(self):
        """Check if this source is already published on the server

        Requires parsing the server URl out of the binary *.ags file, or a server URL from config
        Need to use AGS Rest API (http://resources.arcgis.com/en/help/rest/apiref/index.html)
        """
        logger.debug("Check if %s exists on the server %s", self.service_path, self.server_url)
        if self.server_url is None:
            if self.__service_connection_file_path is not None:
                logger.debug("Server URL is undefined. Trying to get from connection file")
                self.server_url = self.__service_url_from_ags(self.__service_connection_file_path)
        if self.server_url is None:
            logger.debug("Server URL is undefined. Assume service exists")
            return True

        url = self.server_url + '/rest/services?f=json'
        if self.__service_folder_name is not None:
            # Check if the folder is valid
            try:
                json = requests.get(url).json()
                # sample response: {..., "folders":["folder1","folder2"], ...}
                folders = [folder.lower() for folder in json['folders']]
            except Exception as ex:
                logger.warn("Failed to check for service, %s. Assume service exists", ex.message)
                return True
            logger.debug("folders found: %s", folders)
            if self.__service_folder_name.lower() in folders:
                url = self.server_url + '/rest/services/' + self.__service_folder_name + '?f=json'
            else:
                logger.debug("folder was not found on server, so service does not exist yet")
                return False
        logger.debug("looking for services at: %s", url)
        try:
            json = requests.get(url).json()
            # sample response: {..., "services":[{"name": "WebMercator/DENA_Final_IFSAR_WM", "type": "ImageServer"}]}
            services = [service['name'].lower() for service in json['services']]
        except Exception as ex:
            logger.warn("Failed to check for service, %s. Assume service exists", ex.message)
            return True

        logger.debug("services found: %s", services)
        return self.service_path.lower() in services

    def __analyze_draft_service_definition(self):
        """Analyze a Service Definition Draft (.sddraft) files for readiness to publish

        If asked to analyze the file, ignore any existing cached analysis results
        http://desktop.arcgis.com/en/arcmap/latest/analyze/arcpy-mapping/analyzeforsd.htm
        """

        if not self.__have_draft:
            self.__create_draft_service_definition()
        if not self.__have_draft:
            logger.error('Unable to get a draft service definition to analyze')
            return
        # If we created a new draft service definition, then we have results.
        if self.__draft_analysis_result is not None:
            return
        try:
            import arcpy
            logger.info("Begin arcpy.mapping.AnalyzeForSD(%s)", self.__draft_file_name)
            self.__draft_analysis_result = arcpy.mapping.AnalyzeForSD(self.__draft_file_name)
            logger.info("Done arcpy.mapping.AnalyzeForSD()")
        except Exception as ex:
            raise PublishException('Unable to analyze draft service definition: %s', ex.message)
        self.__simplify_and_cache_analysis_results()

    def __simplify_and_cache_analysis_results(self):
        if self.__draft_analysis_result is not None:
            self.__simplify_analysis_results()
            try:
                import json
                with open(self.__issues_file_name, 'wb') as f:
                    f.write(json.dumps(self.__draft_analysis_result))
            except Exception as ex:
                logger.warn("Unable to cache the analysis results: %s", ex.message)

    def __get_analysis_result_from_cache(self):
        if self.__file_exists_and_is_newer(self.__issues_file_name, self.path):
            try:
                import json
                with open(self.__issues_file_name, 'rb') as f:
                    self.__draft_analysis_result = json.load(f)
            except Exception as ex:
                logger.warn('Unable to load or parse the cached analysis results %s', ex.message)

    def __simplify_analysis_results(self):
        """self.__draft_analysis_result is not expressible as JSON (keys must be a string),
        This fixes that, and makes it a little simpler to 'stringify' for reporting
        input: {"warnings":{("msg",code):[layer, layer, ...]}
        output: {"warnings":[{"name":str,"code":int,"layers":["name1", "name2",...]},...]}
        """
        simple_results = {}
        for key in ('messages', 'warnings', 'errors'):
            if key in self.__draft_analysis_result:
                issue_list = []
                issues = self.__draft_analysis_result[key]
                for ((message, code), layerlist) in issues.items():
                    issue = {'text': message,
                             'code': code,
                             'layers': [layer.longName for layer in layerlist]}
                    issue_list.append(issue)
                    simple_results[key] = issue_list
        self.__draft_analysis_result = simple_results

    def __stringify_analysis_results(self):
        """This only works on the simplified version of the analysis results"""
        text = ''
        for key in ('messages', 'warnings', 'errors'):
            if key in self.__draft_analysis_result:
                issues = self.__draft_analysis_result[key]
                if 0 < len(issues):
                    text += key.upper() + '\n-------------------------\n'
                    for issue in issues:
                        text += '  {0} (code {1})\n'.format(issue['text'], issue['code'])
                        layers = issue['layers']
                        if 0 < len(layers):
                            text += '    applies to layers: {0}\n'.format(','.join(layers))
        return text

    def __create_service_definition(self, force=False):
        """Converts a service definition draft (.sddraft) into a service definition

        Once staged, the input draft service definition is deleted.
        Calling is_publishable will check for an existing *.sd file that is newer than source

        http://desktop.arcgis.com/en/arcmap/latest/tools/server-toolbox/stage-service.htm
        """
        if force:
            self.__delete_file(self.__sd_file_name)

        if not self.is_publishable:
            raise PublishException("Service Definition Draft has issues and is not ready to publish")

        if not self.__have_service_definition:
            try:
                import arcpy
                logger.info("Begin arcpy.StageService_server(%s, %s)", self.__draft_file_name, self.__sd_file_name)
                arcpy.StageService_server(self.__draft_file_name, self.__sd_file_name)
                logger.info("Done arcpy.StageService_server()")
                self.__have_service_definition = True
                self.__have_new_service_definition = True
            except Exception as ex:
                raise PublishException('Unable to stage the service definition file: %s', ex.message)

    def __create_replacement_service_draft(self):
        """Modify the service definition draft to overwrite the existing service

        The existing draft file is overwritten.
        Need to check if this is required before calling.
        """
        logger.debug("Fixing draft file %s for replacement", self.__draft_file_name)
        import xml.dom.minidom as dom

        new_type = 'esriServiceDefinitionType_Replacement'
        file_name = self.__draft_file_name

        xdoc = dom.parse(file_name)
        descriptions = xdoc.getElementsByTagName('Type')
        for desc in descriptions:
            if desc.parentNode.tagName == 'SVCManifest':
                if desc.hasChildNodes():
                    logger.debug("Update tag %s from %s to %s", desc.firstChild, desc.firstChild.data, new_type)
                    desc.firstChild.data = new_type

        with open(file_name, u'wb') as f:
            #   File "C:\Python27\ArcGIS10.5\lib\xml\dom\minidom.py", line 1745, in writexml
            #     writer.write('<?xml version="1.0" ?>'+newl)
            #   TypeError: write() argument 1 must be unicode, not str
            xdoc.writexml(f)
        logger.debug("Draft file fixed.")

    def __publish_service(self, force=False):
        # TODO: Support the optional parameters to UploadServiceDefinition_server

        """Publish Service Definition

        Uploads and publishes a GIS service to a specified GIS server based on a staged service definition (.sd) file.
        http://desktop.arcgis.com/en/arcmap/latest/tools/server-toolbox/upload-service-definition.htm

        arcpy.UploadServiceDefinition_server (in_sd_file, in_server, {in_service_name}, {in_cluster}, {in_folder_type},
           {in_folder}, {in_startupType}, {in_override}, {in_my_contents}, {in_public}, {in_organization}, {in_groups})

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
            self.__create_service_definition(force=force)
        if not self.__have_service_definition:
            raise PublishException("Service Definition (*.sd) file is not ready to publish")

        if self.__service_connection_file_path is None:
            # conn = ' '.join([word.capitalize() for word in self.__service_server_type.split('_')])
            conn = 'My Hosted Services'
        else:
            conn = self.__service_connection_file_path

        # only publish if we need to.
        if force or not self.is_live or self.__have_new_service_definition:
            try:
                import arcpy
                logger.info("Begin arcpy.UploadServiceDefinition_server(%s, %s)", self.__sd_file_name, conn)
                arcpy.UploadServiceDefinition_server(self.__sd_file_name, conn)
                logger.info("Done arcpy.UploadServiceDefinition_server()")
            except Exception as ex:
                raise PublishException(ex.message)

    @staticmethod
    def __delete_file(path):
        try:
            logger.debug("deleting %s", path)
            os.remove(path)
        except Exception:
            raise PublishException('Unable to delete {0}'.format(path))

    @staticmethod
    def __file_exists_and_is_newer(new_file, old_file):
        try:
            if not os.path.exists(new_file):
                return False
            if not os.path.exists(old_file):
                return True
            old_mtime = os.path.getmtime(old_file)
            new_mtime = os.path.getmtime(new_file)
            return old_mtime < new_mtime
        except Exception as ex:
            logger.warn("Exception raised checking for file A newer than file B: %s", ex.message)
            return False

    @staticmethod
    def __service_url_from_ags(path):
        """find and return the first 'URL' string in the binary file at path

        The ags file is in utf16, so decode properly to do string searches"""
        url_start = 'http'
        url_end = '/arcgis'
        result = set([])
        with open(path, 'rb') as f:
            data = f.read()
            text = data.decode('utf16')
            # print(text)
            start_index = 0
            while 0 <= start_index:
                start_index = text.find(url_start, start_index)
                # print('start_index', start_index)
                if 0 <= start_index:
                    end_index = text.find(url_end, start_index)
                    # print('end_index', end_index)
                    if 0 <= end_index:
                        url = text[start_index:end_index] + url_end
                        result.add(url)
                        start_index = end_index
        if len(result) == 1:
            return list(result)[0]
        else:
            return None


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


def test_service_check():

    # No need to test no path
    # IDE will give a warning about missing parameter, and we will crash right away (programming error)

    print("test defaults; Issues Warnings")
    doc = Doc(None)
    alive = doc.is_live
    print('Server:', doc.server_url, 'Service', doc.service_path, 'Alive:', alive)
    assert alive

    print("test bad ags file; Issues Warnings")
    doc = Doc(r'.\test_data\test.mxd', server=r'.\test_data\test2.ags')
    alive = doc.is_live
    print('Server:', doc.server_url, 'Service', doc.service_path, 'Alive:', alive)
    assert alive

    print("test missing doc w/o folder; Issues Warnings")
    doc = Doc(r'.\test_data\test.mxd', server=r'.\test_data\real.ags')
    alive = doc.is_live
    print('Server:', doc.server_url, 'Service', doc.service_path, 'Alive:', alive)
    assert not alive

    print("test missing doc in folder (bad); Issues Warnings")
    doc = Doc(r'.\test_data\test.mxd', folder='test', server=r'.\test_data\real.ags')
    alive = doc.is_live
    print('Server:', doc.server_url, 'Service', doc.service_path, 'Alive:', alive)
    assert not alive

    print("test doc (good) in folder (good); Issues Warnings")
    doc = Doc(r'.\test_data\dsm_HS.mxd', folder='Ifsar', server=r'.\test_data\real.ags')
    alive = doc.is_live
    print('Server:', doc.server_url, 'Service', doc.service_path, 'Alive:', alive)
    assert alive


def test_publish():
    doc = Doc(r'c:\tmp\ags_test\test\survey.mxd', folder='test', server=r'c:\tmp\ags_test\ais_admin.ags')
    print('Local name:', doc.name, '|    Service path:', doc.service_path)
    print(doc.issues)
    if not doc.is_publishable:
        print('Not ready to publish!')
    else:
        print('Ready to publish.')
        try:
            doc.publish()
            print("Published!!")
        except PublishException as ex:
            print("Failed to publish", ex.message)


if __name__ == '__main__':
    logger.addHandler(logging.StreamHandler())
    logger.setLevel(logging.DEBUG)
    # test_path_folder_input()
    # test_server_input()
    # test_service_check()
    test_publish()
