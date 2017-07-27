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

    import argparse
    parser = argparse.ArgumentParser(description='Syncs a set of ArcGIS Web Services with source documents')

    if config.root_directory is None:
        parser.add_argument('root_directory', metavar='PATH',  help='The directory of documents to publish.')
    else:
        parser.add_argument('root_directory', nargs='?', metavar='PATH', default=config.root_directory,
                            help=('The directory of documents to publish. '
                                  'The default is {0}').format(config.root_directory))
    parser.add_argument('-v', '--verbose', action='store_true', help='Show informational messages.')
    parser.add_argument('--debug', action='store_true', help='Show extensive debugging messages.')

    args = parser.parse_args()

    if args.verbose:
        logger.parent.handlers[0].setLevel(logging.INFO)
        logger.info("Started logging at INFO level")
    if args.debug:
        logger.parent.handlers[0].setLevel(logging.DEBUG)
        logger.debug("Started logging at DEBUG level")
        logger.debug("Command line argument %s", args)

    return args


def main():
    settings = get_configuration_settings()
    documents = Documents(settings)
    for doc in documents.items_to_publish:
        if doc.is_publishable:
            try:
                doc.publish()
            except PublishException as ex:
                logger.error("Unable to publish %s because %s", doc.name, ex.message)
        else:
            logger.warn("Unable to publish %s because %s", doc.name, doc.issues)
    for doc in documents.items_to_unpublish:
        try:
            doc.unpublish()
        except PublishException as ex:
            logger.error("Unable to remove service for %s because %s", doc.name, ex)


if __name__ == '__main__':
    main()
