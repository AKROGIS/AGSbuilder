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
    def __init__(self, path=None, settings=None):
        self.__path = None
        self.__filesystem_mxds = []
        self.__settings = settings
        self.path = path

    @property
    def path(self):
        return self.__path

    @path.setter
    def path(self, new_value):
        # TODO: Check if valid?
        # TODO: use config value if None
        logger.debug("setting path from %s to %s", self.__path, new_value)
        if new_value == self.__path:
            return
        self.__path = new_value
        self.__filesystem_mxds = self.__get_filesystem_mxds()

    @property
    def items_to_publish(self):
        # TODO: Enhance document creation with details from a spreadsheet
        # TODO: created additional documents (image services) based on data in spreadsheet
        mxds = self.__filesystem_mxds
        logger.debug("found %s documents",len(mxds))
        docs = [Doc(mxd, folder=folder, config=self.__settings) for folder, mxd in mxds]
        return docs

    @property
    def items_to_unpublish(self):
        return [Doc(r'c:\tmp\ags_test\test\survey.mxd', folder='test', config=self.__settings)]

    def __get_filesystem_mxds(self):
        """Looks in the filesystem for map documents to publish
        creates a private list of (folder,fullpath) for each mxd found"""
        mxds = []
        logger.debug("get_filesystem_mxds for %s", self.path)
        if self.path is not None and os.path.isdir(self.path):
            logger.debug("searching %s", self.path)
            mxds = [(None, mxd) for mxd in self.__find_mxds_in_folder(self.path)]
            logger.debug("found %s", len(mxds))
            folders = [name for name in os.listdir(self.path)
                       if os.path.isdir(os.path.join(self.path, name))]
            for folder in folders:
                logger.debug("searching %s", folder)
                path = os.path.join(self.path, folder)
                mxds += [(folder, mxd) for mxd in self.__find_mxds_in_folder(path)]
                logger.debug("found %s", len(mxds))
        return mxds

    @staticmethod
    def __find_mxds_in_folder(folder):
        names = os.listdir(folder)
        mxds = [name for name in names if os.path.splitext(name)[1].lower() == '.mxd']
        paths = [os.path.join(folder, mxd) for mxd in mxds]
        # make sure it is a file, and not some weird directory name
        mxd_filepaths = [path for path in paths if os.path.isfile(path)]
        return mxd_filepaths


def test_path():
    docs = Documents(path="C:/tmp/ags_test")
    for doc in docs.items_to_publish:
        print(doc.name, doc.service_path)

if __name__ == '__main__':
    logger.addHandler(logging.StreamHandler())
    logger.setLevel(logging.DEBUG)
    test_path()
