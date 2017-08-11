from __future__ import absolute_import, division, print_function, unicode_literals
import logging
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

class Documents:
    def __init__(self, settings):
        self.__settings = settings

    @property
    def items_to_publish(self):
        return []  # Doc("my.mxd", config=self.__settings)]

    @property
    def items_to_unpublish(self):
        return [Doc(r'c:\tmp\ags_test\test\survey.mxd', folder='test', config=self.__settings)]
