from __future__ import absolute_import, division, print_function, unicode_literals
import logging.config
import config_logger
from document_finder import Documents
from publishable_doc import PublishException

logging.config.dictConfig(config_logger.config)
logging.raiseExceptions = False
logger = logging.getLogger('main')
logger.info("Logging Started")


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
    config.history_file = getattr(config, 'history_file', None)
    config.service_list = getattr(config, 'service_list', None)
    config.server = getattr(config, 'server', None)
    config.server_url = getattr(config, 'server_url', None)
    config.admin_username = getattr(config, 'admin_username', None)
    config.admin_password = getattr(config, 'admin_password', None)

    import argparse
    parser = argparse.ArgumentParser(description='Syncs a set of ArcGIS Web Services with source documents')

    if config.root_directory is None:
        parser.add_argument('root_directory', metavar='PATH',  help='The directory of documents to publish.')
    else:
        parser.add_argument('root_directory', nargs='?', metavar='PATH', default=config.root_directory,
                            help=('The directory of documents to publish. '
                                  'The default is {0}').format(config.root_directory))
    parser.add_argument('--history_file', default=config.history_file,
                        help=('The history_file is a path to a csv file with records of the '
                              'services published. It is used to determine what services are '
                              'orphaned and should be unpublished.  If None the server is '
                              'queried for the current list of all services regardless of '
                              'source. '
                              'The default is {0}').format(config.history_file))
    parser.add_argument('--service_list', default=config.service_list,
                        help=('The service_list is a path to a csv file with records of services '
                              'to be published. This will be considered along with the files found '
                              'in the root_directory. It can be used to publish image services and '
                              'provide non-default publishing parameters. '
                              'The default is {0}').format(config.service_list))
    parser.add_argument('-s', '--server', default=config.server,
                        help=('The server to publish to. Must be a path to a connection (*.ags) file, '
                              'or MY_HOSTED_SERVICES (the default if None is provided). '
                              'MY_HOSTED_SERVICES uses the Portal configured in ArcGIS Desktop Administrator and '
                              'your windows credentials. '
                              'The default is {0}').format(config.server))
    parser.add_argument('--server_url', default=config.server_url,
                        help=('The base URL to the server hosting the services. If None, '
                              'it may be extracted from the *.ags file provided for SERVER. '
                              'Used for checking on and removing services. '
                              'The default is {0}').format(config.server_url))
    parser.add_argument('-u', '--admin_username', default=config.admin_username,
                        help=('The name of an admin account on the server hosting the services. '
                              'Used for removing services. '
                              'The default is {0}').format(config.admin_username))
    parser.add_argument('-p', '--admin_password', default=config.admin_password,
                        help=('The password for the admin account. '
                              'If not provided, the value in config.py is used'))
    parser.add_argument('-v', '--verbose', action='store_true', help='Show informational messages.')
    parser.add_argument('--debug', action='store_true', help='Show extensive debugging messages.')

    args = parser.parse_args()

    if args.verbose:
        logger.parent.handlers[0].setLevel(logging.INFO)
        logger.info("Started logging at INFO level")
    if args.debug:
        logger.parent.handlers[0].setLevel(logging.DEBUG)
        logger.debug("Started logging at DEBUG level")
        redacted_password = args.admin_password
        args.admin_password = 'XX_redacted_XX'
        logger.debug("Command line argument %s", args)
        args.admin_password = redacted_password

    return args


def main():
    settings = get_configuration_settings()
    documents = Documents(config=settings)
    for doc in documents.items_to_publish:
        if doc.is_publishable:
            try:
                doc.publish()
            except PublishException as ex:
                logger.error("Unable to publish %s because %s", doc.name, ex.message)
        else:
            logger.warn("Unable to publish %s because %s", doc.name, doc.errors)
    for doc in documents.items_to_unpublish:
        try:
            doc.unpublish()
        except PublishException as ex:
            logger.error("Unable to remove service for %s because %s", doc.name, ex)


if __name__ == '__main__':
    main()
