from __future__ import absolute_import, division, print_function, unicode_literals
import os.path
import logging
import requests
from io import open  # for python2/3 compatibility

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


def get_service_url_from_ags_file(path):
    """find and return the first 'URL' string in the binary file at path

    The ags file is in utf16, so decode properly to do string searches"""
    if path is None or not os.path.exists(path):
        logger.warning("No valid path provided to get_service_url_from_ags_file()")
        return None

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


def get_services_from_server(server_url):
    logger.debug("Get list of services on server %s", server_url)

    if server_url is None:
        logger.warn("Unable to get services (No server_url is defined)")

    url = server_url + '/rest/services?f=json'

    try:
        json = requests.get(url).json()
        # sample response: {..., "folders":["folder1","folder2"], ...}
        root_services = json['services']
        folders = json['folders']
    except Exception as ex:
        logger.error("Failed to get services on %s: %s", server_url, ex.message)
        return None
    services = [(None, service) for service in root_services]
    for folder in folders:
        folder_services = get_services_from_server_folder(server_url, folder)
        if folder_services is None:
            return None
        services += [(folder, service) for service in folder_services]


def get_services_from_server_folder(server_url, folder):
    logger.debug("Get list of services on server %s in folder %s", server_url, folder)

    if server_url is None:
        logger.warn("Unable to get services (No server_url is defined)")
        return None

    if folder is None:
        url = server_url + '/rest/services?f=json'
    else:
        url = server_url + '/rest/services/' + folder + '?f=json'
    try:
        json = requests.get(url).json()
        # sample response: {..., "services":[{"name": "WebMercator/DENA_Final_IFSAR_WM", "type": "ImageServer"}]}
        services = json['services']
    except Exception as ex:
        logger.error("Failed to get services from server %s in folder %s: %s", server_url, folder, ex.message)
        return None
    return services


def service_path(mxd_path, folder=None):
    if mxd_path is None:
        return None
    name = os.path.splitext(os.path.basename(mxd_path))[0]
    new_name = sanitize_service_name(name)
    if folder is None:
        return None, new_name
    new_folder = sanitize_service_name(folder)
    return new_folder, new_name


def sanitize_service_name(name, replacement='_'):
    """Replace all non alphanumeric characters with replacement

    The name can only contain alphanumeric characters and underscores.
    No spaces or special characters are allowed.
    The name cannot be more than 120 characters in length.
    http://desktop.arcgis.com/en/arcmap/latest/analyze/arcpy-mapping/createmapsddraft.htm"""

    if name is None:
        return None
    clean_chars = [c if c.isalnum() else replacement for c in name]
    return ''.join(clean_chars)[:120]
