from __future__ import absolute_import, division, print_function, unicode_literals
import logging
import os.path
from publishable_doc import Doc

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
    def __init__(self, path=None, history=None, settings=None):
        self.__path = None
        self.__history = None
        self.__filesystem_mxds = []
        self.__settings = settings
        self.path = path
        self.history = history

    @property
    def path(self):
        return self.__path

    @path.setter
    def path(self, new_value):
        """Set the file system path to search for *.mxd files"""
        # TODO: Check if valid?
        # TODO: use settings if None
        if new_value == self.__path:
            return
        logger.debug("setting path from %s to %s", self.__path, new_value)
        self.__path = new_value
        self.__filesystem_mxds = self.__get_filesystem_mxds()

    @property
    def history(self):
        """Returns a list of tuples [(source_path,service_folder,service_name),..]
        These are services that have been previously published, and not deleted"""
        return self.__history

    @history.setter
    def history(self, new_value):
        """Can be a path, or a list of tuples
        If it is a path, then it should contain a csv file with source_path,service_folder,service_name"""
        # TODO: Check if valid?
        # TODO: use settings if None
        # TODO: If still none, get for the server in the settings
        if new_value == self.__history:
            return
        logger.debug("setting history from %s to %s", self.__history, new_value)
        self.__history = new_value

    @property
    def items_to_publish(self):
        # TODO: Enhance document creation with details from a spreadsheet
        # TODO: created additional documents (image services) based on data in spreadsheet
        mxds = self.__filesystem_mxds
        logger.debug("Found %s documents to publish", len(mxds))
        docs = [Doc(mxd, folder=folder, config=self.__settings) for folder, mxd in mxds]
        return docs

    @property
    def items_to_unpublish(self):
        if self.history is None:
            return []
        mxds = self.__filesystem_mxds
        # TODO: if history is lengthy, and mxds is empty, it might be the sign of a problem. Should we delete all?
        docs = []
        source_paths = set([path for _,path in mxds])
        for path, folder, name in self.history:
            if path not in source_paths:
                # TODO: add service_name to the Doc init properties
                docs.append(Doc(path, folder=folder, config=self.__settings))
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


def test_path():
    docs = Documents(path="C:/tmp/ags_test")
    for doc in docs.items_to_publish:
        print(doc.name, doc.service_path)

if __name__ == '__main__':
    logger.addHandler(logging.StreamHandler())
    logger.setLevel(logging.DEBUG)
    test_path()
