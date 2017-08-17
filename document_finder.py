from __future__ import absolute_import, division, print_function, unicode_literals
import logging
import os.path
from io import open  # for python2/3 compatibility
from publishable_doc import Doc
import util

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


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

class Documents(object):
    def __init__(self, path=None, history=None, service_list=None, config=None):
        self.__path = None
        self.__history = None
        self.__service_list = None
        self.__filesystem_mxds = []
        self.__config = config

        if path is not None:
            self.path = path
        else:
            try:
                self.path = self.__config.root_directory
            except AttributeError:
                self.path = None

        if history is not None:
            self.history = history
        else:
            try:
                self.history = self.__config.history_file
            except AttributeError:
                self.history = self.__get_history_from_server()

        if service_list is not None:
            self.service_list = service_list
        else:
            try:
                self.service_list = self.__config.service_list
            except AttributeError:
                self.service_list = None

    @property
    def path(self):
        return self.__path

    @path.setter
    def path(self, new_value):
        """Set the file system path to search for *.mxd files"""
        if new_value == self.__path:
            return
        logger.debug("setting path from %s to %s", self.__path, new_value)
        if new_value is not None and os.path.isdir(new_value):
            self.__path = new_value
            self.__filesystem_mxds = self.__get_filesystem_mxds()
        else:
            logger.debug("Path is None or not found, There are no filesystem_mxds")
            self.__path = None
            self.__filesystem_mxds = []

    @property
    def history(self):
        """Returns a list of tuples [(source_path,service_folder,service_name),..]
        These are services that have been previously published, and not deleted"""
        return self.__history

    @history.setter
    def history(self, new_value):
        """Can be a path, or a list of tuples
        If it is a path, then it should contain a csv file with source_path,service_folder,service_name"""
        if new_value == self.__history:
            return
        logger.debug("setting history from %s to %s", self.__history, new_value)
        self.__history = new_value
        if new_value is None:
            return
        if isinstance(new_value, list):
            if len(new_value) == 0 or (isinstance(new_value[0], tuple) and len(new_value[0]) == 3):
                return
            else:
                self.__history = None
                logger.warn("History list must have 3-tuple members, Setting history to None")
        else:
            if os.path.isfile(new_value):
                self.__history = self.__get_history_from_file(new_value)

    @property
    def service_list(self):
        """Returns a list of tuples [(source_path,service_folder,service_name),..]
        These are services that have been previously published, and not deleted"""
        return self.__service_list

    @service_list.setter
    def service_list(self, new_value):
        """Can be a path, or a list of tuples
        If it is a path, then it should contain a csv file with source_path,service_folder,service_name"""
        if new_value == self.__service_list:
            return
        logger.debug("setting service list from %s to %s", self.__service_list, new_value)
        self.__service_list = new_value
        if new_value is None:
            return
        if isinstance(new_value, list):
            if len(new_value) == 0 or (isinstance(new_value[0], tuple) and len(new_value[0]) == 3):
                return
            else:
                self.__service_list = None
                logger.warn("Service list must have 3-tuple members, Setting list to None")
        else:
            if os.path.isfile(new_value):
                self.__service_list = self.__get_server_list_from_file(new_value)

    @property
    def items_to_publish(self):
        # TODO: Enhance document creation with details from a spreadsheet
        # TODO: created additional documents (image services) based on data in spreadsheet
        mxds = self.__filesystem_mxds
        logger.debug("Found %s documents to publish", len(mxds))
        docs = [Doc(mxd, folder=folder, config=self.__config) for folder, mxd in mxds]
        return docs

    @property
    def items_to_unpublish(self):
        # TODO: unpublish documents flagged in the spreadsheet
        if self.history is None:
            return []
        mxds = self.__filesystem_mxds
        if len(mxds) == 0:
            logger.warn("No *.mxd files found, Unwilling to unpublish all without an override.")
            # TODO: support an override to unpublish all?
            return []
        docs = []
        source_paths = set([path for _, path in mxds])
        service_paths = [util.service_path(path, folder) for folder, path in mxds]
        service_paths = [(name if folder is None else folder + "/" + name).lower()
                         for folder, name in service_paths]
        service_paths = set(service_paths)
        for path, folder, name in self.history:
            if path is None:
                # check if folder/name matches what would come from one of our mxds, if so, then keep it
                service_path = (name if folder is None else folder + "/" + name).lower()
                if service_path not in service_paths:
                    docs.append(Doc(path, folder=folder, service_name=name, config=self.__config))
            else:
                if path not in source_paths:
                    docs.append(Doc(path, folder=folder, service_name=name, config=self.__config))
        logger.debug("Found %s documents to UN-publish", len(docs))
        return docs

    def __get_filesystem_mxds(self):
        """Looks in the filesystem for map documents to publish
        creates a private list of (folder,fullpath) for each mxd found"""
        mxds = []
        if self.path is not None and os.path.isdir(self.path):
            mxds = [(None, mxd) for mxd in self.__find_mxds_in_folder(self.path)]
            folders = [name for name in os.listdir(self.path)
                       if os.path.isdir(os.path.join(self.path, name))]
            for folder in folders:
                path = os.path.join(self.path, folder)
                mxds += [(folder, mxd) for mxd in self.__find_mxds_in_folder(path)]
        return mxds

    def __get_history_from_server(self):
        """Get a list of services on the server provided in the configuration settings"""
        server = None
        try:
            server = self.__config.server_url
        except AttributeError:
            logger.info("server_url not defined in the configuration settings")
        if server is None:
            conn_file = None
            try:
                conn_file = self.__config.server
            except AttributeError:
                logger.info("server not defined in the configuration settings")
            server = util.get_service_url_from_ags_file(conn_file)
        if server is None:
            logger.info("Unable to get services (No server_url is defined)")
            return None
        services = util.get_services_from_server(server)
        logger.debug("Found %s services at %s", len(services), server)
        history = [(None, folder, name) for folder, name in services]
        return history

    @staticmethod
    def __find_mxds_in_folder(folder):
        logger.debug("Searching %s for *.mxd files", folder)
        names = os.listdir(folder)
        mxds = [name for name in names if os.path.splitext(name)[1].lower() == '.mxd']
        paths = [os.path.join(folder, mxd) for mxd in mxds]
        # make sure it is a file, and not some weird directory name
        mxd_filepaths = [path for path in paths if os.path.isfile(path)]
        logger.debug("Found %s *.mxd files in %s", len(mxd_filepaths), folder)
        return mxd_filepaths

    @staticmethod
    def __get_history_from_file(path):
        """Read a publishing history from a csv file.

        The first row of the file will be skipped (assumed to be a header row).
        The file must have at least three columns which will be interpreted as text for
        a full file path to a service source, a service folder, and a service name"""
        try:
            import csv
            history = []
            with open(path, "rb") as f:
                csv_reader = csv.reader(f)
                header = csv_reader.next()
                if len(header) < 3:
                    raise IndexError("file does not have at least 3 rows")
                for row in csv_reader:
                    history.append(row[:3])
            return history
        except Exception as ex:
            logger.warn("Unable to parse the file %s: %s", path, ex)
            return None

    @staticmethod
    def __get_server_list_from_file(path):
        """Read a list of services to publish from a csv file.

        The first row of the file will be skipped (assumed to be a header row).
        The file must have at least X columns which will be interpreted as text for ..."""
        # TODO: define the service list file format
        try:
            import csv
            services = []
            with open(path, "rb") as f:
                csv_reader = csv.reader(f)
                header = csv_reader.next()
                if len(header) < 3:
                    raise IndexError("file does not have at least 3 rows")
                for row in csv_reader:
                    services.append(row[:3])
            return services
        except Exception as ex:
            logger.warn("Unable to parse the file %s: %s", path, ex)
            return None


def test_path():
    docs = Documents(path="C:/tmp/ags_test")
    for doc in docs.items_to_publish:
        print(doc.name, doc.service_path)

if __name__ == '__main__':
    logger.addHandler(logging.StreamHandler())
    logger.setLevel(logging.DEBUG)
    test_path()
