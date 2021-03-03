# -*- coding: utf-8 -*-
"""
Tests for a document publishable as a web service.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import logging

from publishable_doc import Doc, PublishException

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.DEBUG)


def test_path_folder_input():
    """Test the Doc when created with Doc(path).

    No need to test Doc(), IDE will give a warning about missing parameter,
    and we will crash right away (programming error)
    """
    print("test path is None; Issues Warning")
    doc = Doc(None)
    print("Local name:", doc.name, "|    Service path:", doc.service_path)
    assert doc.name is None and doc.service_path is None

    print("test path is int; Issues Warning")
    doc = Doc(1)
    print("Local name:", doc.name, "|    Service path:", doc.service_path)
    assert doc.name is None and doc.service_path is None

    print("test path is junk text; Issues Warning")
    doc = Doc("junk")
    print("Local name:", doc.name, "|    Service path:", doc.service_path)
    assert doc.name is None and doc.service_path is None

    print("test path is valid file; no folder")
    doc = Doc(r".\test_data\test.mxd")
    print("Local name:", doc.name, "|    Service path:", doc.service_path)
    assert doc.name == "test" and doc.service_path == "test"

    print("test path is valid file; folder is None")
    doc = Doc(r".\test_data\test.mxd", folder=None)
    print("Local name:", doc.name, "|    Service path:", doc.service_path)
    assert doc.name == "test" and doc.service_path == "test"

    print("test path is valid file; folder is int; Issues Warning")
    doc = Doc(r".\test_data\folder\test2.mxd", folder=1)
    print("Local name:", doc.name, "|    Service path:", doc.service_path)
    assert doc.name == "test2" and doc.service_path == "test2"

    print("test path is valid file; folder is text")
    doc = Doc(r".\test_data\folder\test2.mxd", folder="folder")
    print("Local name:", doc.name, "|    Service path:", doc.service_path)
    assert doc.name == "folder/test2" and doc.service_path == "folder/test2"

    print("test path is invalid file; folder is text; Issues Warning")
    doc = Doc(r".\test_data\folder\test.mxd", folder="folder")
    print("Local name:", doc.name, "|    Service path:", doc.service_path)
    assert doc.name is None and doc.service_path is None

    print("test path is valid file; folder is text (both have special characters)")
    doc = Doc(r".\test_data\my weird name!.mxd", folder="%funky folder%")
    print("Local name:", doc.name, "|    Service path:", doc.service_path)
    assert (
        doc.name == "%funky folder%/my weird name!"
        and doc.service_path == "_funky_folder_/my_weird_name_"
    )

    print("test path is valid file; folder is text (both have special characters)")
    doc = Doc(r".\test_data\%funky folder%\test3.mxd", folder="%funky folder%")
    print("Local name:", doc.name, "|    Service path:", doc.service_path)
    assert (
        doc.name == "%funky folder%/test3"
        and doc.service_path == "_funky_folder_/test3"
    )


def test_server_input():
    """Test the Doc when created with a server in the config."""

    # pylint: disable=too-many-statements)
    # pylint: disable=useless-object-inheritance,too-few-public-methods

    class TestConfig(object):
        """A simple Config with only a server for testing."""

        server = None

        def __init__(self):
            pass

    config = TestConfig()
    print("test no config object (no warning; use default)")
    doc = Doc(r".\test_data\test.mxd")
    print("    Server:", doc.server)
    assert doc.server == "MY_HOSTED_SERVICES"

    print("test no server attribute on config (no warning; use default)")
    doc = Doc(r".\test_data\test.mxd", config=config)
    print("    Server:", doc.server)
    assert doc.server == "MY_HOSTED_SERVICES"

    print("test config.server is None (no warning; use default)")
    setattr(config, "server", None)
    doc = Doc(r".\test_data\test.mxd", config=config)
    print("    Server:", doc.server)
    assert doc.server == "MY_HOSTED_SERVICES"

    print("test config.server is int (should warn and use default)")
    config.server = 1
    doc = Doc(r".\test_data\test.mxd", config=config)
    print("    Server:", doc.server)
    assert doc.server == "MY_HOSTED_SERVICES"

    print("test config.server is junk text (should warn and use default)")
    config.server = "junk"
    doc = Doc(r".\test_data\test.mxd", config=config)
    print("    Server:", doc.server)
    assert doc.server == "MY_HOSTED_SERVICES"

    print("test config.server is file (no warning; use file)")
    config.server = r".\test_data\test.ags"
    doc = Doc(r".\test_data\test.mxd", config=config)
    print("    Server:", doc.server)
    assert doc.server == r".\test_data\test.ags"

    print("test config.server is MY_HOSTED_SERVICES (no warning; use setting)")
    config.server = "MY_HOSTED_SERVICES"
    doc = Doc(r".\test_data\test.mxd", config=config)
    print("    Server:", doc.server)
    assert doc.server == "MY_HOSTED_SERVICES"

    print("test service parameter is None (no warning; should use config)")
    config.server = r".\test_data\test.ags"
    doc = Doc(r".\test_data\test.mxd", server=None, config=config)
    print("    Server:", doc.server)
    assert doc.server == r".\test_data\test.ags"

    print("test service parameter is int (should warn and use default)")
    doc = Doc(r".\test_data\test.mxd", server=1, config=config)
    print("    Server:", doc.server)
    assert doc.server == "MY_HOSTED_SERVICES"

    print("test service parameter is junk text (should warn and use default)")
    doc = Doc(r".\test_data\test.mxd", server="junk", config=config)
    print("    Server:", doc.server)
    assert doc.server == "MY_HOSTED_SERVICES"

    print("test service parameter is is file (no warning; use file)")
    doc = Doc(r".\test_data\test.mxd", server=r".\test_data\test2.ags", config=config)
    print("    Server:", doc.server)
    assert doc.server == r".\test_data\test2.ags"

    print("test service parameter is MY_HOSTED_SERVICES (no warning; use setting")
    doc = Doc(r".\test_data\test.mxd", server="MY_HOSTED_SERVICES", config=config)
    print("    Server:", doc.server)
    assert doc.server == "MY_HOSTED_SERVICES"


def test_service_check():
    """Test the Doc when created with Doc(path, server).

    No need to test Doc(), IDE will give a warning about missing parameter,
    and we will crash right away (programming error)
    """
    print("test defaults; Issues Warnings")
    doc = Doc(None)
    alive = doc.is_live
    print("Server:", doc.server_url, "Service", doc.service_path, "Alive:", alive)
    assert alive

    print("test bad ags file; Issues Warnings")
    doc = Doc(r".\test_data\test.mxd", server=r".\test_data\test2.ags")
    alive = doc.is_live
    print("Server:", doc.server_url, "Service", doc.service_path, "Alive:", alive)
    assert alive

    print("test missing doc w/o folder; Issues Warnings")
    doc = Doc(r".\test_data\test.mxd", server=r".\test_data\real.ags")
    alive = doc.is_live
    print("Server:", doc.server_url, "Service", doc.service_path, "Alive:", alive)
    assert not alive

    print("test missing doc in folder (bad); Issues Warnings")
    doc = Doc(r".\test_data\test.mxd", folder="test", server=r".\test_data\real.ags")
    alive = doc.is_live
    print("Server:", doc.server_url, "Service", doc.service_path, "Alive:", alive)
    assert not alive

    print("test doc (good) in folder (good); Issues Warnings")
    doc = Doc(r".\test_data\dsm_HS.mxd", folder="Ifsar", server=r".\test_data\real.ags")
    alive = doc.is_live
    print("Server:", doc.server_url, "Service", doc.service_path, "Alive:", alive)
    assert alive


def test_publish():
    """Test publishing a Doc."""

    doc = Doc(
        r"c:\tmp\ags_test\test\survey.mxd",
        folder="test",
        server=r"c:\tmp\ags_test\ais_admin.ags",
    )
    print("Local name:", doc.name, "|    Service path:", doc.service_path)
    print(doc.all_issues)
    if not doc.is_publishable:
        print("Not ready to publish!")
        print(doc.errors)
    else:
        print("Ready to publish.")
        try:
            doc.publish()
            print("Published!!")
        except PublishException as ex:
            print("Failed to publish", ex)


if __name__ == "__main__":
    test_path_folder_input()
    # test_server_input()
    # test_service_check()
    # test_publish()
